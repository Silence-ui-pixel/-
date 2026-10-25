"""认证与鉴权：JWT 签发/校验、密码哈希、当前用户依赖。

Sprint 1 只做最小闭环：login 签发 JWT + get_current_user 解析。
种子账号的密码哈希见 db/seed.sql（当前是占位符，正式上线前要换真实 bcrypt）。
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

# 开发用的签名密钥。生产必须从环境变量注入，绝不能写死。
# 长度需 ≥32 字节（HMAC-SHA256 最低要求）。
SECRET_KEY = "canku-dev-secret-key-please-change-in-production-2026"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 小时，覆盖一个班次

_bearer = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, role: str, username: str) -> str:
    """签发 JWT。payload 里放 user_id / role / username，供后续鉴权用。"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "username": username,
        "exp": datetime.now(UTC) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """校验并解析 JWT。失败抛 401。"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="token 已过期，请重新登录") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="无效的 token") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """从 Authorization: Bearer <jwt> 解析当前用户，返回 {id, role, username}。

    这里只做「身份识别」，不做「角色鉴权」——角色鉴权由具体接口自己判断
    （如对账接口需要 MANAGER）。
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="缺少认证信息")

    payload = decode_token(credentials.credentials)
    return {
        "id": int(payload["sub"]),
        "role": payload["role"],
        "username": payload["username"],
    }
