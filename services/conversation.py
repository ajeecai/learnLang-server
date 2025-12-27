import io
import logging
from typing import Dict, Union
from websocket.protocol import WebSocketProtocol
from services.chat_sessions import ChatSessionManager
from utils.transcribe import transcribe_file
from utils.synthesize import synthesize_text

logger = logging.getLogger(__name__)


async def handle_conversation(
    parsed_data: Dict[str, Union[Dict, bytes]],
    username: str,
) -> bytes:
    """
    处理 WebSocket 的 conversation 消息（TYPE_DATA, data_type=conversation）。
    执行音频转录、LLM 交互和语音合成，返回二进制响应。
    """
    logger.info("It is conversation audio from client")
    audio_file = io.BytesIO(parsed_data["binary_data"])
    logger.info(f"audio_file size {len(audio_file.getvalue())}")

    # 使用单例获取 ChatSessionManager
    chat_session_manager = ChatSessionManager.get_instance()

    transcription = await transcribe_file(audio_file)
    chat_session = await chat_session_manager.get_session(username)
    await chat_session.add_message("user", transcription)
    response = await chat_session.conversation_with_llm(transcription)
    logger.info(f"response from LLM is: {response}")

    reply_text = response
    first_pipe_index = response.find("|")
    if first_pipe_index != -1:
        reply_text = response[:first_pipe_index].strip()

    await chat_session.add_message("assistant", reply_text)
    audio_stream = await synthesize_text(reply_text)

    # 构造响应
    response_data = {
        "json_data": {"A": transcription, "B": response},
        "binary_data": audio_stream,
    }
    return WebSocketProtocol.build_message(
        direction=1, type_=WebSocketProtocol.TYPE_DATA, **response_data
    )
