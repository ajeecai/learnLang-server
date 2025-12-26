# 系统操作
import os
import logging

# JWT 和密码处理
from jose import JWTError, jwt
from passlib.context import CryptContext

# FastAPI 安全
from fastapi.security import OAuth2PasswordBearer

# FastAPI 核心模块
from fastapi import (
    Depends,
    HTTPException,
    status,
    WebSocket,
)

# 异步 MySQL 数据库
from aiomysql import create_pool
from aiomysql.cursors import DictCursor

# 时间和日期处理
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-please-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# JWT 辅助函数
def get_expiry_time(token):
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"]).get(
        "exp", float("inf")
    )


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 数据库连接
async def get_db():
    async with create_pool(
        host="db",
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "mysqlpassword"),
        db=os.getenv("MYSQL_DATABASE", "stts"),
        cursorclass=DictCursor,
    ) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                yield conn, cursor


# HTTP token 提取
async def get_token_http(token: str = Depends(oauth2_scheme)):
    """
    从 HTTP 请求的 Authorization 头提取 token。
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# WebSocket token 提取
async def get_token_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        raise ValueError("Invalid token")
    return token


# 通用用户验证
async def get_current_user(
    token: str = Depends(get_token_http), db_and_cursor: tuple = Depends(get_db)
):
    """
    验证 JWT token 并返回用户。
    默认用于 HTTP 端点，WebSocket 端点会覆盖 token 依赖。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await get_user(username, db_and_cursor)

    if user is None:
        raise credentials_exception

    logger.info(f"get_current_user: {username}")

    return user


async def get_user(username: str, db_and_cursor: tuple = Depends(get_db)):
    db, cursor = db_and_cursor
    await cursor.execute(
        "SELECT username, hashed_password FROM users WHERE username = %s", (username,)
    )
    user = await cursor.fetchone()
    if user:
        return {
            "username": user["username"],
            "hashed_password": user["hashed_password"],
        }
    return None
