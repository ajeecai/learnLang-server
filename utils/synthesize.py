import os
import asyncio
import logging
import soundfile as sf
from io import BytesIO
from TTS.api import Synthesizer
from scipy.signal import butter, lfilter

logger = logging.getLogger(__name__)

device = os.getenv("DEVICE", "cpu")
logger.info(f"device in synthesize : {device}")

def lowpass_filter(wav, sr, cutoff=5000, order=6):
    nyq = 0.5 * sr
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, wav)

# 设置模型路径
model_path = os.path.join("/whisper_models","my_tts_models")

# model_name = "tts_models--en--ljspeech--tacotron2-DDC"  # 美式英语, not good
# model_name = "tts_models--en--ljspeech--glow-tts"  # 美式英语, not good
# model_name = "tts_models--en--vctk--vits" # 英式英语
# model_name = "tts_models--en--ljspeech--vits"  # OK, 4.3s
# model_name = "tts_models--multilingual--multi-dataset--your_tts" # speaker #3,4,5 (ascendly) is OK, 1.3s
model_name = "tts_models--en--jenny--jenny" # good, but very slow,5s with GPU. 语速不能控制
# model_name = "tts_models--multilingual--multi-dataset--xtts_v2"  # good, 30 sec with GPU

model_dir = os.path.join(model_path, model_name)

# 拼接各个配置文件路径
config_path = os.path.join(model_dir, "config.json")
model_checkpoint = os.path.join(model_dir, "model_file.pth")
# speakers_file = os.path.join(model_dir, "speaker_ids.json")
speakers_file = os.path.join(model_dir, "speakers.json")
languages_file = os.path.join(model_dir, "language_ids.json")

multi = False
# overwrite the parameters
if model_name.find('jenny') > 1:
    model_checkpoint = os.path.join(model_dir, "model.pth") 

if model_name.find('xtts_v2') > 1: 
    model_checkpoint = model_dir
    tts_speakers_file = os.path.join(model_dir, "speakers_xtts.pth")
    languages_file = None
    multi = True

# 加载模型
synthesizer = Synthesizer(
    tts_checkpoint=model_checkpoint,
    tts_config_path=config_path,
    # tts_speakers_file=speakers_file,
    # tts_languages_file=languages_file,
    use_cuda=True if device == "cuda" else False,
)
# # 获取支持的说话人和语言
if multi:
    speakers = synthesizer.tts_model.speaker_manager.speaker_names
    languages = synthesizer.tts_model.language_manager.language_names

    print(f"可用说话人：{speakers}")
    print(f"可用语言： {languages}")

    # # 选择一个你喜欢的说话人和语言（例如取第一个）
    # speaker = speakers[5]
    # language = languages[0]

async def synthesize_text(text: str) -> bytes:
    """
    合成语音并保存为文件。
    参数:
        text (str): 要合成的文本
        output_path (str): 输出音频文件路径
    """

    # 获取当前事件循环
    loop = asyncio.get_running_loop()
    # 将阻塞任务卸载到线程池
    def blocking_synthesize():
        # 生成语音
        wav = synthesizer.tts(
            text,
            # speaker_name="Claribel Dervla",
            # language_name="en",
            # length_scale=1.0,      # 稍快的语速，听起来更有精神
            # noise_scale=0.5,       # 更高的随机性，语调更自然有起伏
            # noise_scale_w=0.8      # 控制情感变化幅度，略大一点更欢快
        )
        return wav
        # wav = lowpass_filter(wav, sr=synthesizer.output_sample_rate)
        # synthesizer.save_wav(wav, path=output_path)

    wav = await loop.run_in_executor(None, blocking_synthesize)

    # Convert NumPy array to MP3 bytes, if None, return empty stream
    wav_buffer = BytesIO()
    if wav is not None:
        sf.write(wav_buffer, wav, synthesizer.output_sample_rate, format="MP3")
        logger.info(f"Synthesized audio size: {wav_buffer.tell()} bytes")
        wav_buffer.seek(0)

    return wav_buffer
