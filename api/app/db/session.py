from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# pool_pre_ping：连接池里的连接被数据库单方面断开后会被自动丢弃重建。
# 开发环境热重载频繁，不加这个会经常碰到 "connection is closed"。
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每请求一个 Session。

    注意：这里不提交事务。写操作必须在业务层显式 commit，
    并且只能经由 stock_service —— 见 db/README 与 03-data-model.html。
    """
    async with SessionLocal() as session:
        yield session
