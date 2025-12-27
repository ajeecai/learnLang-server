import logging
from typing import Dict, Callable, Optional, Union

logger = logging.getLogger(__name__)


class WsDataHandlerRegistry:
    """
    管理 WebSocket TYPE_DATA 消息的处理器映射。
    注意：websocket/handlers.py 处理所有的协议消息类型（PING, DATA 等），
    而本类专门负责处理 TYPE_DATA 分支下的具体数据业务逻辑分发（根据 json_data["data_type"]）。
    例如: {"data_type": "conversation", ...}
    """

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}

    def register(self, data_type: str, handler: Callable):
        """注册新的 TYPE_DATA 处理器"""
        self.handlers[data_type] = handler
        logger.info(f"Registered handler for data_type: {data_type}")

    async def dispatch(self, parsed_data: Dict, username: str) -> Optional[bytes]:
        """分发 TYPE_DATA 消息到对应处理器"""
        data_type = parsed_data["json_data"].get("data_type")
        if not data_type:
            logger.error("Missing 'data_type' field in TYPE_DATA")
            return None

        handler = self.handlers.get(data_type)
        if not handler:
            logger.error(f"No handler for data_type: {data_type}")
            return None

        try:
            return await handler(parsed_data, username)
        except Exception as e:
            logger.error(f"Handler error for {data_type}: {e}")
            return None
