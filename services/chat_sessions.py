import json
import os
import redis.asyncio as redis
from collections import deque
from typing import Dict, List
import logging
import asyncio
import aiohttp
from fastapi import HTTPException

# env vars passed from docker-compose, Dockerfile to here
LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")
HTTP_PROXY = os.getenv("HTTP_PROXY")

MAX_TOKENS_ONCE = 500
MAX_TOKENS_TOTAL = 1000
# MAX_TOKENS_TOTAL = 12000

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis 客户端（异步）
redis_client = redis.Redis(
    host="redis",  # 替换为你的 Redis 主机
    port=6379,  # 替换为你的 Redis 端口
    db=0,
    decode_responses=True,  # 自动解码为字符串
)

system_prompt = (
    "You are a helpful English teacher to have a chat with a student, alway reply in English. "
    "Correct error on grammar, for example student sai 'Why you did not to school? I go to school yesterday',"
    "You said 'You should say: Why didnt you go to school? I went to school yesterday'."
    "Do not repeat sentences without error when correct me."
    "Besides, bring up interesting topic trying to use some tough IELTS vocabulary, no more than 100 words in reply."
    "For tough words in your reply, put all of them  (at least one or two) at the end in format without any prefix, example for bureaucracy:"
    " | bureaucracy: /bjʊəˈrɒkrəsi/,官僚主义，官僚机构| perspicacious: /ˌpɜː.spɪˈkeɪ.ʃəs/,目光敏锐的，判断力强的 |. "
    " This part is not mandatory if there is no."
)

# TODO: don't allow username with special chars
class ChatSession:
    def __init__(
        self,
        system_prompt: str = system_prompt,
        max_tokens: int = MAX_TOKENS_ONCE,
        username: str = None,
    ):
        """
        创建一个新的对话会话，存储在 Redis 中。
        :param system_prompt: GPT 系统角色设定
        :param max_tokens: 最大上下文 token 数
        :param username: 用户名，用于 Redis 键
        """
        self.system_message = {"role": "system", "content": system_prompt}
        self.max_tokens = max_tokens
        self.username = username
        self.messages = deque([self.system_message])  # 初始化包含 system 消息
        if username:
            asyncio.create_task(self._save_to_redis())  # 异步保存到 Redis

    @classmethod
    def get_instance(cls) -> "ChatSessionManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def conversation_with_llm(self, my_words: str) -> str:
        """
        与 LLM 交互，发送用户消息并获取回复。
        :param my_words: 用户输入
        :return: LLM 回复
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}",
            }
            payload = {
                "model": LLM_MODEL,
                "messages": self.get_messages()
                + [{"role": "user", "content": my_words}],
                # 节省token，不带上下文
                # "messages": [{"role": "assistant", "content": system_prompt}] + [{"role": "user", "content": my_words}],
                "max_tokens": MAX_TOKENS_ONCE,
            }
            # logger.info(f"header {headers}, payload {payload}")
            try:
                async with session.post(
                    LLM_API_URL, headers=headers, json=payload, proxy=HTTP_PROXY
                ) as response:
                    if response.status != 200:
                        logger.error(
                            f"LLM API request failed: {response.status} - {response.reason}"
                        )
                        raise HTTPException(
                            status_code=500, detail="Failed to communicate with LLM"
                        )
                    data = await response.json()
                    # logger.info(f"response is {response}")
                    content = data["choices"][0]["message"]["content"]
                    return content
            except aiohttp.ClientError as e:
                logger.error(f"LLM API error: {str(e)}")
                raise HTTPException(status_code=500, detail="LLM API error")

    # TODO: for simplicity, don't consider multiple chat with same username
    async def add_message(self, role: str, content: str):
        """
        添加新消息并自动清理旧消息，更新 Redis。
        :param role: 消息角色（user/assistant）
        :param content: 消息内容
        """
        self.messages.append({"role": role, "content": content})
        self._truncate_to_max_tokens()
        if self.username:
            await self._save_to_redis()

    def get_messages(self) -> List[Dict[str, str]]:
        """
        获取当前会话的所有消息。
        """
        return list(self.messages)

    def _estimate_tokens(self, message: Dict[str, str]) -> int:
        """
        估算单个消息的 token 数（简化为单词数 * 1.3）。
        """
        return int(len(message["content"].split()) * 1.3)

    def _total_tokens(self) -> int:
        """
        计算所有消息的总 token 数。
        """
        return sum(self._estimate_tokens(m) for m in self.messages)

    def _truncate_to_max_tokens(self):
        """
        如果总 token 数超过限制，移除最早的 user/assistant 消息，保留 system 消息。
        """
        while self._total_tokens() > self.max_tokens and len(self.messages) > 1:
            self.messages.popleft()
            if self.messages[0]["role"] == "system":
                continue
            else:
                break

    async def _save_to_redis(self):
        """
        将会话数据保存到 Redis，使用分布式锁防止并发覆盖。
        """
        if not self.username:
            return
        lock = redis_client.lock(
            f"lock:chat:{self.username}",
            timeout=5,  # 锁 5 秒后自动释放
            blocking_timeout=1,  # 最多等待 1 秒获取锁
        )
        async with lock:
            try:
                session_data = {
                    "system_prompt": self.system_message["content"],
                    "max_tokens": self.max_tokens,
                    "messages": list(self.messages),
                }
                await redis_client.set(
                    f"chat_session:{self.username}", json.dumps(session_data)
                )
                logger.debug(f"Saved session for user: {self.username}")
            except redis.RedisError as e:
                logger.error(
                    f"Failed to save session to Redis for user {self.username}: {str(e)}"
                )

    @classmethod
    async def load_from_redis(cls, username: str) -> "ChatSession":
        """
        从 Redis 加载会话，如果不存在则返回 None。
        """
        try:
            session_data = await redis_client.get(f"chat_session:{username}")
            if session_data:
                data = json.loads(session_data)
                session = cls(
                    system_prompt=data["system_prompt"],
                    max_tokens=data["max_tokens"],
                    username=username,
                )
                session.messages = deque(data["messages"])
                logger.debug(f"Loaded session for user: {username}")
                return session
            logger.debug(f"No session found for user: {username}")
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(
                f"Failed to load session from Redis for user {username}: {str(e)}"
            )
            return None


# uvicorn --workers N 多 worker 不会导致多线程竞争使用单例的问题，
# 但会导致每个进程有自己的 ChatSessionManager 实例，会话通过redis来保持同步
class ChatSessionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatSessionManager, cls).__new__(cls)
            cls._instance.sessions = {}
            logger.info("ChatSessionManager singleton initialized")
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ChatSessionManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_session(
        self,
        username: str,
        system_prompt: str = system_prompt,
        max_tokens: int = MAX_TOKENS_TOTAL,
    ) -> ChatSession:
        """
        获取或创建用户会话。
        :param username: 用户名
        :param system_prompt: 系统提示（用于新会话）
        :param max_tokens: 最大 token 数（用于新会话）
        :return: ChatSession 对象
        """
        if username in self.sessions:
            return self.sessions[username]

        session = await ChatSession.load_from_redis(username)
        if session:
            self.sessions[username] = session
            return session

        session = ChatSession(
            system_prompt=system_prompt, max_tokens=max_tokens, username=username
        )
        self.sessions[username] = session
        return session

    # TODO: clean up sessions using asyncio.create_task
    # async def cleanup_sessions(self, ttl_seconds: int = 3600):
    #     async with self._redis as r:
    #         keys = await r.keys("session:*")
    #         current_time = time.time()
    #         for key in keys:
    #             session_data = await r.get(key)
    #             session = json.loads(session_data)
    #             if session.get("last_active", current_time) <= current_time - ttl_seconds:
    #                 await r.delete(key)
    #         logger.debug(f"Cleaned up sessions, remaining: {len(await r.keys('session:*'))}")

    # async def add_message(self, username: str, role: str, content: str):
    #     """
    #     向用户会话添加消息。
    #     """
    #     session = await self.get_session(username, system_prompt=system_prompt)
    #     await session.add_message(role, content)

    # async def get_messages(self, username: str) -> List[Dict[str, str]]:
    #     """
    #     获取用户会话的消息列表。
    #     """
    #     session = await self.get_session(username, system_prompt=system_prompt)
    #     return session.get_messages()
