import time
import logging

from typing import Dict, Callable, Optional
from fastapi import WebSocket
from .protocol import WebSocketProtocol

logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, data_handler: Optional[Callable] = None):
        """
        WebSocket 消息处理器。
        :param data_handler: 可选的 TYPE_DATA 消息处理器，接受 parsed_data 和 username，返回 bytes。
        """
        self.data_handler = data_handler

    async def handle_ping(self, context: Dict) -> bytes:
        """处理 ping 消息，返回 pong"""
        logger.debug("Received ping")
        context["last_ping"] = time.time()
        return WebSocketProtocol.build_message(
            direction=1, type_=WebSocketProtocol.TYPE_PONG
        )

    async def handle_data(self, parsed_data: Dict, username: str) -> Optional[bytes]:
        """处理 TYPE_DATA 消息，调用注册的处理器"""
        if self.data_handler is None:
            logger.error("No data handler registered for TYPE_DATA")
            return None
        try:
            return await self.data_handler(parsed_data, username)
        except Exception as e:
            logger.error(f"Data handler error: {e}")
            return WebSocketProtocol.build_message(
                direction=1,
                type_=WebSocketProtocol.TYPE_DATA,
                json_data={"error": str(e)},
            )

    async def handle_push_response(self, parsed_data: Dict) -> None:
        """处理推送消息回应"""
        logger.info(f"Received push response: {parsed_data['json_data']}")

    async def handle_timeout(self, websocket: WebSocket) -> None:
        """处理超时通知"""
        logger.warning("Received client timeout notification")
        await websocket.close(code=1000)
