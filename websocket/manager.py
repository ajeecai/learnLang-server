import asyncio
import time
import logging
from fastapi import WebSocket
from .protocol import WebSocketProtocol

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self, websocket: WebSocket, token_expiry_time: float):
        self.websocket = websocket
        self.context = {"last_ping": time.time()}
        self.token_expiry_time = token_expiry_time
        self.timeout_task = None

    async def start(self):
        """启动超时和推送任务"""
        self.timeout_task = asyncio.create_task(self.check_timeout_and_expiry())
        # self.push_task = asyncio.create_task(self.push_messages())

    async def check_timeout_and_expiry(self):
        """检查超时和 token 过期"""
        while True:
            current_time = time.time()
            logger.debug(
                f"check_timeout_and_expiry: {current_time}, {self.context['last_ping']}"
            )
            if current_time - self.context["last_ping"] > 90:
                await self.websocket.send_bytes(
                    WebSocketProtocol.build_message(
                        direction=0, type_=WebSocketProtocol.TYPE_TIMEOUT
                    )
                )
                logger.info("WebSocket timeout due to no ping")
                await self.websocket.close(code=1000)
                break
            if current_time > self.token_expiry_time:
                await self.websocket.send_bytes(
                    WebSocketProtocol.build_message(
                        direction=0, type_=WebSocketProtocol.TYPE_TOKEN_EXPIRED
                    )
                )
                logger.info("WebSocket timeout due to token expired")
                await self.websocket.close(code=1008)
                break
            await asyncio.sleep(30)

    async def push_messages(self):
        """定期推送消息"""
        while True:
            await asyncio.sleep(10)
            json_content = {"text1": "Server Push", "text2": f"At {time.time()}"}
            push_message = WebSocketProtocol.build_message(
                direction=0, type_=WebSocketProtocol.TYPE_PUSH, json_data=json_content
            )
            await self.websocket.send_bytes(push_message)
            logger.info("Pushed message")

    def cancel_tasks(self):
        """取消后台任务"""
        if self.timeout_task:
            self.timeout_task.cancel()
        # if self.push_task:
        #     self.push_task.cancel()
