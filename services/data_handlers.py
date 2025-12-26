import logging
from typing import Dict, Callable, Optional, Union

logger = logging.getLogger(__name__)


class DataHandlerRegistry:
    """管理 WebSocket TYPE_DATA 消息的处理器映射"""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}

    def register(self, msg_type: str, handler: Callable):
        """注册新的 TYPE_DATA 处理器"""
        self.handlers[msg_type] = handler
        logger.info(f"Registered handler for msg_type: {msg_type}")

    async def dispatch(self, parsed_data: Dict, username: str) -> Optional[bytes]:
        """分发 TYPE_DATA 消息到对应处理器"""
        msg_type = parsed_data["json_data"].get("msg")
        if not msg_type:
            logger.error("Missing msg type in TYPE_DATA")
            return None

        handler = self.handlers.get(msg_type)
        if not handler:
            logger.error(f"No handler for msg_type: {msg_type}")
            return None

        try:
            return await handler(parsed_data, username)
        except Exception as e:
            logger.error(f"Handler error for {msg_type}: {e}")
            return None
