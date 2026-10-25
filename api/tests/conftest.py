"""pytest 夹具。

apply_txn 的测试必须连真实 PostgreSQL（验证 FOR UPDATE 行锁、
生成列 qty_available、对账视图 v_inventory_recon），SQLite 无法模拟。

关键：engine 必须是 function-scoped（每个测试在自己的事件循环里
创建/销毁），因为 pytest-asyncio 默认每个 async 测试用独立事件循环，
跨循环复用 engine 会报 "Event loop is closed"。
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


@pytest.fixture
async def session_factory():
    """返回一个 async_sessionmaker，用于测试内开多个独立连接（并发测试）。"""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def session():
    """独立 session，测试结束后关闭（engine 也随之释放）。"""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()
    await engine.dispose()


@pytest.fixture
async def clean_tables(session):
    """清空库存相关表，保证测试隔离。"""
    # stock_txn 只追加，不能 delete；测试环境直接 TRUNCATE 绕过触发器
    await session.execute(text("TRUNCATE stock_txn, inventory RESTART IDENTITY CASCADE"))
    await session.commit()
    yield


@pytest.fixture
async def base_ids(clean_tables, session):
    """返回一个已存在的 sku_id 和 location_id（来自种子数据）。"""
    r = await session.execute(
        text("select id, sku_code from sku where sku_code = 'SKU-1001'")
    )
    sku = r.first()
    assert sku is not None, "种子数据里应有 SKU-1001，先跑 db-init"

    r = await session.execute(
        text("select id from location where location_code = 'WH01-A-01-01-01'")
    )
    loc = r.first()
    assert loc is not None, "种子数据里应有库位 WH01-A-01-01-01"

    return {"sku_id": sku.id, "location_id": loc.id, "sku_code": sku.sku_code}
