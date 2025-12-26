import logging
import re
from fastapi import Request
from starlette.types import Message

logger = logging.getLogger(__name__)


def register_http_logging(app):
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """
        FastAPI 中间件，用于记录 HTTP 请求的详细信息。
        记录包括方法、URL、头信息、请求体，并隐藏敏感信息（如密码和令牌）。
        仅在 DEBUG 日志级别启用时记录详细内容。
        """
        if not logger.isEnabledFor(logging.DEBUG):
            return await call_next(request)

        logger.info("Middleware: Processing request")

        # 提取请求信息
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)

        # 读取请求体
        body = await request.body()
        body_str = body.decode("utf-8", errors="ignore") if body else ""
        if len(body_str) > 150:
            body_str = body_str[:150] + "..."  # 截断过长的请求体

        # 隐藏敏感信息：密码
        if body_str:
            body_str = re.sub(r"(?i)(password\s*[:=]\s*)(\S+)", r"\1***", body_str)

        # 隐藏敏感信息：Bearer 令牌
        for key, value in headers.items():
            if "authorization" in key.lower() and value.lower().startswith("bearer "):
                headers[key] = "Authorization: Bearer [HIDDEN]"

        # 构造请求日志内容
        request_lines = [f"{method} {url.replace(str(request.base_url), '/')} HTTP/1.1"]
        for key, value in headers.items():
            request_lines.append(f"{key.capitalize()}: {value}")
        if body_str:
            request_lines.append("")
            request_lines.append(body_str)

        # 记录请求详情
        logger.debug("Request:\n" + "\n".join(request_lines))

        # 构造新的请求对象以继续处理
        async def receive() -> Message:
            return {"type": "http.request", "body": body, "more_body": False}

        new_request = Request(request.scope, receive=receive)
        response = await call_next(new_request)

        # 记录响应状态
        logger.debug(f"Response status: {response.status_code}")
        return response
