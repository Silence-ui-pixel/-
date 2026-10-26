"""认证路由：login / users/me / users 列表。"""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user, require_role
from app.db.models import AppUser
from app.db.session import get_session
from app.schemas import (
    LoginRequest,
    LoginResponse,
    PageMeta,
    User,
    UserListItem,
    UserListResponse,
)

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


@router.get("/users", response_model=UserListResponse, summary="用户列表（需 MANAGER/ADMIN）")
async def list_users(
    keyword: str | None = None,
    role: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current: dict = Depends(require_role("ADMIN", "MANAGER")),
    session: AsyncSession = Depends(get_session),
) -> UserListResponse:
    """用户分页列表，供用户管理页使用。

    两个约束必须守住：
    1. **绝不返回 password_hash** —— 用 UserListItem 而不是直接序列化 ORM 对象，
       这是白名单式的字段控制，比「记得排除某字段」可靠。
    2. **需 MANAGER/ADMIN** —— 用户名单属于管理信息，OPERATOR/VIEWER 不该看到。
    """
    stmt = select(AppUser)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            AppUser.username.ilike(like) | AppUser.display_name.ilike(like)
        )
    if role:
        stmt = stmt.where(AppUser.role == role)

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    users = (
        await session.execute(
            stmt.order_by(AppUser.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    return UserListResponse(
        items=[
            UserListItem(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                role=u.role,
                status=u.status,
            )
            for u in users
        ],
        meta=PageMeta(total=total, page=page, page_size=page_size),
    )
