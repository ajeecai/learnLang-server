from faster_whisper import WhisperModel
import os, asyncio
import logging
from typing import Union, BinaryIO

logger = logging.getLogger(__name__)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
device = os.getenv("DEVICE", "cpu")

logger.info(f"device in transcribe : {device}")

model_path = os.path.join("/whisper_models", "faster-whisper-large-v3")
model = WhisperModel(model_path, device=device, compute_type="int8")


async def transcribe_file(audio_path: Union[str, BinaryIO]) -> str:
    """
    转录音频文件为文本。
    参数:
        audio_path (str | BinaryIO): 音频文件路径或文件对象
    返回:
        str: 转录的文本
    """

    # 获取当前事件循环, use ProcessPoolExecutor for even better performance
    loop = asyncio.get_running_loop()
    # 将阻塞任务卸载到线程池
    def blocking_transcribe():
        segments, _ = model.transcribe(audio_path, word_timestamps=True)
        return " ".join(segment.text for segment in segments)

    return await loop.run_in_executor(None, blocking_transcribe)
