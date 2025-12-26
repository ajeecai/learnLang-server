from TTS.utils.manage import ModelManager
import os
import subprocess

from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

# 设置代理（根据你本地代理端口调整）
os.environ["HTTP_PROXY"] = os.getenv("HTTP_PROXY", "")
os.environ["HTTPS_PROXY"] = os.getenv("HTTP_PROXY", "")

print(f"HTTP_PROXY: {os.getenv('HTTP_PROXY')}")

model_base_dir = os.getenv("MODEL_BASE_DIR", "")
if not model_base_dir:
    print(f"MODEL_BASE_DIR不存在!!!")
    exit(-1)

tts_model_dir = os.path.join(model_base_dir, "my_tts_models")
os.makedirs(tts_model_dir, exist_ok=True)
os.environ["TTS_CACHE_DIR"] = tts_model_dir

# 1. Download STT (Speech-to-Text) models
# 更改工作目录
os.chdir(model_base_dir)

# 设置环境变量并执行 git clone
env = os.environ.copy()  # 复制当前环境变量
env["GIT_LFS_PROGRESS"] = "1"  # 设置 GIT_LFS_PROGRESS=1
try:
    subprocess.run(
        ["git", "clone", "https://huggingface.co/Systran/faster-whisper-large-v3"],
        env=env,
        check=True,  # 如果命令失败，抛出异常
    )
except subprocess.CalledProcessError as e:
    print(f"error: {e}")

# 2. download TTS models

# 实例化模型管理器
manager = ModelManager()

# tts --list_models to see all model names
# 要下载的模型列表
models = [
    "tts_models/en/ljspeech/tacotron2-DDC",  # 美式英语
    "tts_models/en/vctk/vits",  # 英式英语
    "tts_models/en/ljspeech/glow-tts",
    "tts_models/en/ljspeech/vits",
    "tts_models/multilingual/multi-dataset/your_tts",
    "tts_models/en/ljspeech/speedy-speech",
    "tts_models/en/jenny/jenny",
    "tts_models/multilingual/multi-dataset/xtts_v2",
]

# 下载模型前先检查是否存在
for model_name in models:
    model_folder_name = model_name.replace("/", "--")
    final_path = os.path.join(tts_model_dir, model_folder_name)
    download_path = final_path
    print(f"download_path: {download_path}")
    print(f"final_path: {final_path}")

    # 如果文件夹已存在，跳过下载
    if os.path.exists(final_path):
        print(f"✅ 已存在: {model_name} -> {final_path}")
        continue

    # 下载模型
    print(f"⬇️ 正在下载: {model_name}")
    manager.download_model(model_name)

    # 移动到指定目录下并重命名为带双横线的结构，便于区分
    if os.path.exists(download_path):
        os.rename(download_path, final_path)
        print(f"✅ 下载完成: {download_path} -> {final_path}")
    else:
        print(f"❌ 下载失败: {model_name}")
