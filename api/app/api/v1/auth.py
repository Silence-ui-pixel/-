"""认证路由：login / users/me。"""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user
from app.db.models import AppUser
from app.db.session import get_session
from app.schemas import LoginRequest, LoginResponse, User

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse, summary="登录换取 JWT")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    """用户名密码换 JWT。种子账号见 db/seed.sql。"""
    user = (
        await session.execute(
            select(AppUser).where(AppUser.username == body.username)
        )
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 校验密码（bcrypt）。开发环境种子哈希见 seed.sql。
    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user.id, user.role, user.username)
    return LoginResponse(access_token=token, token_type="bearer")


@router.get("/users/me", response_model=User, summary="当前用户信息")
async def get_me(
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """返回当前登录用户信息（前端控制菜单用）。"""
    user = await session.get(AppUser, current["id"])
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return User(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )
