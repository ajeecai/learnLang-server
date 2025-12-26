import logging
from services.data_handlers import DataHandlerRegistry
from services.conversation import handle_conversation

logger = logging.getLogger(__name__)


def configure_handlers(registry: DataHandlerRegistry):
    """
    配置 WebSocket TYPE_DATA 消息的处理器。
    在此注册所有 msg_type 和对应的处理器函数。
    """
    # 注册 conversation 处理器
    registry.register("conversation", handle_conversation)

    # 示例：注册其他处理器（用户可在此添加）
    # registry.register("analytics", handle_analytics)

    logger.info("Completed handler configuration")
