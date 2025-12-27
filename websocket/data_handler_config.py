import logging
from websocket.data_handlers import WsDataHandlerRegistry
from services.conversation import handle_conversation

logger = logging.getLogger(__name__)


def ws_configure_data_handlers(registry: WsDataHandlerRegistry):
    """
    配置 WebSocket TYPE_DATA 消息的处理器。
    这些 handler 只是为了 websocket 里面的 data 处理进行 dispatch 的。
    在此注册所有 data_type 和对应的处理器函数。
    """
    # 注册 conversation 处理器
    registry.register("conversation", handle_conversation)

    # 示例：注册其他处理器（用户可在此添加）
    # registry.register("analytics", handle_analytics)

    logger.info("Completed handler configuration")
