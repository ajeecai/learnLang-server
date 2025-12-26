import logging
from jose import jwt
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from .protocol import WebSocketProtocol
from .handlers import WebSocketHandler
from .manager import WebSocketManager
from auth import get_token_websocket, get_current_user, get_db
from services.chat_sessions import ChatSessionManager
from services.conversation import handle_conversation

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket, chat_session_manager: ChatSessionManager
):
    db_gen = None
    try:
        token = await get_token_websocket(websocket)
        db_gen = get_db()
        db_and_cursor = await anext(db_gen)
        current_user = await get_current_user(token, db_and_cursor=db_and_cursor)
        token_expiry_time = jwt.decode(
            token, "your-secret-key-please-change-this", algorithms=["HS256"]
        ).get("exp", float("inf"))
    except Exception as e:
        await websocket.close(code=1008, reason=f"Invalid token: {str(e)}")
        logger.warning(f"Invalid token: {e}")
        return
    finally:
        if db_gen is not None:
            await db_gen.aclose()

    await websocket.accept()
    manager = WebSocketManager(websocket, token_expiry_time)

    # 注入 conversation 处理器
    async def data_handler(parsed_data, username):
        return await handle_conversation(parsed_data, username)

    handler = WebSocketHandler(data_handler=data_handler)
    await manager.start()

    try:
        while True:
            data = await websocket.receive_bytes()
            if not isinstance(data, bytes):
                continue

            message = WebSocketProtocol.parse_message(data)
            if not message:
                continue

            direction = message["direction"]
            type_ = message["type"]
            payload = message["payload"]

            if direction == 0:  # 客户端消息
                if type_ == WebSocketProtocol.TYPE_PING:
                    pong_message = await handler.handle_ping(manager.context)
                    await websocket.send_bytes(pong_message)
                elif type_ == WebSocketProtocol.TYPE_DATA:
                    parsed_data = WebSocketProtocol.parse_data_payload(payload)
                    logger.info(f"Received data, length: {message['length']} bytes")
                    logger.info(f"Parsed data JSON: {parsed_data['json_data']}")
                    response_message = await handler.handle_data(
                        parsed_data, current_user["username"]
                    )
                    if response_message:
                        await websocket.send_bytes(response_message)
            elif direction == 1:  # 回应
                parsed_data = WebSocketProtocol.parse_data_payload(payload)
                if type_ == WebSocketProtocol.TYPE_PUSH:
                    await handler.handle_push_response(parsed_data)
                elif type_ == WebSocketProtocol.TYPE_TIMEOUT:
                    await handler.handle_timeout(websocket)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        manager.cancel_tasks()
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1000)
