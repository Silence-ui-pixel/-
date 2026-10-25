"""库位相关的查询与策略。

这里只做「选哪个库位」的判断，不写库存 —— 库存变动一律走 stock_service.apply_txn。

三个功能位（location_type）的分工：
    RECEIVING  收货暂存：货到了但没上架。账上有货，但不算「可拣」
    STAGING    发货暂存：已拣出但没发运。仍在账上，账实一致的最后一环
    STORAGE    存储位：正常存放区，拣货从这里出
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.db.models import Inventory, Location


async def get_functional_location(
    session: AsyncSession, location_type: str
) -> Location:
    """按功能类型取一个可用库位（RECEIVING / STAGING）。

    这两类库位在仓库里通常各只有一个，所以取第一个即可。
    取不到时明确报错，而不是静默用错位置 —— 静默用错位会让账实不符，
    而且事后很难查。
    """
    stmt = (
        select(Location)
        .where(Location.location_type == location_type, Location.status == 1)
        .order_by(Location.id)
        .limit(1)
    )
    loc = (await session.execute(stmt)).scalar_one_or_none()
    if loc is None:
        raise NotFound(
            message=f"仓库里没有可用的 {location_type} 库位，请先建一个",
            detail={"location_type": location_type},
        )
    return loc


async def get_receiving_location(session: AsyncSession) -> Location:
    """收货暂存位。"""
    return await get_functional_location(session, "RECEIVING")


async def get_staging_location(session: AsyncSession) -> Location:
    """发货暂存位。"""
    return await get_functional_location(session, "STAGING")


async def pick_putaway_target(
    session: AsyncSession, sku_id: int, exclude_location_id: int | None = None
) -> Location:
    """为上架挑一个存储位（调用方没指定 to_location_id 时）。

    策略（Sprint 1 只做最朴素的两条，够用且可解释）：
      1. 已有同 SKU 且未满的存储位 —— 合并存放，减少碎片，拣货少跑
      2. 否则取 pick_seq 最小的存储位 —— 保证确定性，同一批货总进同一个位

    更复杂的策略（按 ABC 分类、按体积/重量、按周转率）属算法层，不在本阶段。
    """
    # 1. 已有同 SKU 的存储位，且未超容量
    stmt = (
        select(Location)
        .join(Inventory, Inventory.location_id == Location.id)
        .where(
            Location.location_type == "STORAGE",
            Location.status == 1,
            Inventory.sku_id == sku_id,
            Inventory.qty_on_hand > 0,
        )
        .order_by(Location.pick_seq.asc().nulls_last(), Location.id)
        .limit(1)
    )
    if exclude_location_id:
        stmt = stmt.where(Location.id != exclude_location_id)
    loc = (await session.execute(stmt)).scalar_one_or_none()
    if loc is not None:
        # 有容量上限时再校验一次，避免把货堆到已满的位
        if loc.capacity_qty is None:
            return loc
        used = (
            await session.execute(
                select(func.coalesce(func.sum(Inventory.qty_on_hand), 0)).where(
                    Inventory.location_id == loc.id
                )
            )
        ).scalar_one()
        if float(used) < float(loc.capacity_qty):
            return loc

    # 2. 退化为 pick_seq 最小的空闲存储位
    stmt2 = (
        select(Location)
        .where(Location.location_type == "STORAGE", Location.status == 1)
        .order_by(Location.pick_seq.asc().nulls_last(), Location.id)
        .limit(1)
    )
    if exclude_location_id:
        stmt2 = stmt2.where(Location.id != exclude_location_id)
    loc = (await session.execute(stmt2)).scalar_one_or_none()
    if loc is None:
        raise NotFound(
            message="仓库里没有可用的 STORAGE 库位，无法上架",
            detail={"location_type": "STORAGE"},
        )
    return loc
