# ================= 阶段 0: 构建ubuntu:22.04 base镜像  ================
# 主要是为了避免apt update重编，导致stts-api的requirements.txt耗时重编
FROM ubuntu:22.04 AS base
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip git curl build-essential espeak-ng\
    && rm -rf /var/lib/apt/lists/*
# ================= 阶段 1: 构建 stt and tts api 服务镜像 ================
FROM base AS stts-api

ARG HTTP_PROXY
ENV HTTP_PROXY=${HTTP_PROXY}

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt /app/

# 安装 Python 依赖
RUN pip install -r requirements.txt --no-cache-dir

# 下载并安装 cuDNN, https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/linux-x86_64/
RUN curl --http1.1 ${HTTP_PROXY:+-x $HTTP_PROXY} -L -o cudnn.tar.xz \
    https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/linux-x86_64/cudnn-linux-x86_64-9.1.0.70_cuda11-archive.tar.xz \
    && tar -xf cudnn.tar.xz

RUN mkdir -p /usr/local/cuda/include /usr/local/cuda/lib64 \
    && cp -r cudnn-linux-x86_64-9.1.0.70_cuda11-archive/include/* /usr/local/cuda/include/ \
    && cp -r cudnn-linux-x86_64-9.1.0.70_cuda11-archive/lib/* /usr/local/cuda/lib64/ \
    && rm -rf cudnn-linux-x86_64-9.1.0.70_cuda11-archive* cudnn.tar.xz

ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

RUN pip install aiofiles aiomysql pypinyin webrtcvad numpy 'uvicorn[standard]' websockets wsproto aiohttp redis

ARG LLM_API_URL
ARG LLM_API_KEY
ARG LLM_MODEL

ENV LLM_API_URL=${LLM_API_URL} \
    LLM_API_KEY=${LLM_API_KEY} \
    LLM_MODEL=${LLM_MODEL}

# 暴露 API 端口
EXPOSE 8000

ENV PYTHONPATH=/app

COPY app.py /app/
COPY auth /app/auth/
COPY utils /app/utils/
COPY middleware /app/middleware/
COPY services /app/services/
COPY websocket /app/websocket/


# 运行 API, will consume GPU memory * workers
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ================= 阶段 2: 构建 Nginx 服务镜像 ================
FROM nginx:latest AS stts-nginx

ARG DOMAIN_NAME

# 安装 envsubst
RUN apt-get update && apt-get install -y gettext-base curl netcat-openbsd && rm -rf /var/lib/apt/lists/*

# 复制 Nginx 配置文件
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf.template
COPY deploy/nginx/nginx-md5-reload.sh /nginx-md5-reload.sh

RUN chmod +x /nginx-md5-reload.sh && mkdir -p /run && chmod 755 /run

# 复制入口脚本
COPY deploy/nginx/nginx_entrypoint.sh /entrypoint.sh

# 设置入口脚本权限
RUN chmod +x /entrypoint.sh

# 设置入口点
ENTRYPOINT ["/entrypoint.sh"]

# 确保证书目录存在
RUN mkdir -p /certs

# 暴露 HTTPS 端口
EXPOSE 80 443

# 运行 Nginx，动态替换环境变量
CMD ["/bin/sh", "-c", "envsubst '$SSL_CERT_PATH $SSL_KEY_PATH' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;' & /nginx-md5-reload.sh"]

# ================= 阶段 3: 构建 MySQL 数据库镜像 ================
FROM mysql:8.0 AS stts-mysql

COPY ./.init_db.sql /docker-entrypoint-initdb.d/init_db.sql