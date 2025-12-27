# FastAPI 核心模块
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    HTTPException,
    status,
    Form,
    WebSocket,
)

from auth import *
from middleware.http_logging import register_http_logging
from websocket.endpoint import websocket_endpoint

# FastAPI 安全和响应模块
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

# 日志和异步处理
import logging
import os

# 科学计算和音频处理
import numpy as np
import webrtcvad

# 自定义功能模块
from utils.transcribe import transcribe_file
from utils.synthesize import synthesize_text
from websocket.data_handlers import WsDataHandlerRegistry
from websocket.data_handler_config import ws_configure_data_handlers
from services.chat_sessions import ChatSessionManager

# # 设置日志级别（默认 INFO
# log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()


# 初始化 logger
def setup_logging(log_level="INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),  # 输出到控制台
            # logging.FileHandler("app.log")  # 可选：写入文件
        ],
    )
    # 降低第三方模块的日志级别
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("mysql.connector").setLevel(logging.WARNING)


log_level = os.getenv("LOG_LEVEL", "INFO").upper()
setup_logging(log_level)
logger = logging.getLogger(__name__)

# FastAPI 实例
app = FastAPI()
ws_data_handler_registry = WsDataHandlerRegistry()
ws_configure_data_handlers(ws_data_handler_registry)
chat_session_manager = ChatSessionManager.get_instance()

# Initialize VAD
vad = webrtcvad.Vad()
vad.set_mode(3)  # Most aggressive mode


# 中间件：记录请求详细信息
register_http_logging(app)


# 登录端点
@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_and_cursor: tuple = Depends(get_db),
):
    user = await get_user(form_data.username, db_and_cursor)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


# 语音转文字端点（需要认证）
@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # 使用 transcribe.py 的 transcribe_file 函数
    transcription = await transcribe_file(file.file)

    logger.debug(f"Transcription result: {transcription}")

    return {"transcription": transcription}


# 文字转语音端点（需要认证）
@app.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    audio_stream = await synthesize_text(text)
    return StreamingResponse(audio_stream, media_type="audio/wav")


# chat（需要认证）
@app.post("/conversation")
async def conversation_with_llm(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # logger.info(f'current_user {current_user}')
    transcription = await transcribe_file(file.file)
    chat_session = await chat_session_manager.get_session(current_user["username"])
    await chat_session.add_message("user", transcription)
    response = await chat_session.conversation_with_llm(transcription)
    logger.info(f"response from LLM is: {response}")
    await chat_session.add_message("assistant", response)
    audio_stream = await synthesize_text(response)
    return StreamingResponse(audio_stream, media_type="audio/wav")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket_endpoint(websocket, ws_data_handler_registry)
