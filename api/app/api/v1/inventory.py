"""库存读接口：库存余额 / 流水 / 对账。

注意：这里只有「读」，没有任何「写」入口。库存的唯一写入口是
stock_service.apply_txn，契约层也不存在 POST /inventory。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Inventory, Location, Sku, StockTxn
from app.db.session import get_session
from app.schemas import (
    InventoryItem,
    InventoryListResponse,
    PageMeta,
    ReconItem,
    ReconResponse,
    StockTxnItem,
    StockTxnListResponse,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/inventory", response_model=InventoryListResponse, summary="库存余额查询")
async def list_inventory(
    sku_code: str | None = None,
    location_code: str | None = None,
    location_type: str | None = None,
    batch_no: str | None = None,
    expiring_days: int | None = None,
    only_available: bool = False,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> InventoryListResponse:
    """库存余额查询，join sku/location 带出编码和名称。"""
    stmt = (
        select(Inventory, Sku, Location)
        .join(Sku, Inventory.sku_id == Sku.id)
        .join(Location, Inventory.location_id == Location.id)
    )
    if sku_code:
        stmt = stmt.where(Sku.sku_code.ilike(f"%{sku_code}%"))
    if location_code:
        stmt = stmt.where(Location.location_code.ilike(f"%{location_code}%"))
    if location_type:
        stmt = stmt.where(Location.location_type == location_type)
    if batch_no:
        stmt = stmt.where(Inventory.batch_no.ilike(f"%{batch_no}%"))
    if expiring_days is not None:
        # N 天内到期：expiry_date 在当前到 N 天后之间，且不是哨兵值
        stmt = stmt.where(
            Inventory.expiry_date <= func.current_date() + text(f"interval '{expiring_days} days'"),
            Inventory.expiry_date != text("date '9999-12-30'"),
        )
    if only_available:
        stmt = stmt.where(Inventory.qty_available > 0)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(Inventory.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    items = [
        InventoryItem(
            sku_id=inv.sku_id,
            sku_code=sku.sku_code,
            sku_name=sku.name,
            location_id=inv.location_id,
            location_code=loc.location_code,
            location_type=loc.location_type,
            batch_no=inv.batch_no,
            expiry_date=inv.expiry_date,
            qty_on_hand=float(inv.qty_on_hand),
            qty_allocated=float(inv.qty_allocated),
            qty_available=float(inv.qty_available),
            base_uom=sku.base_uom,
        )
        for inv, sku, loc in rows
    ]
    return InventoryListResponse(
        items=items, meta=PageMeta(total=total, page=page, page_size=page_size)
    )


@router.get("/stock-txn", response_model=StockTxnListResponse, summary="库存流水查询")
async def list_stock_txn(
    sku_code: str | None = None,
    txn_type: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> StockTxnListResponse:
    """流水查询，join sku/location 带出编码。含 AI 来源过滤。"""
    stmt = (
        select(StockTxn, Sku, Location)
        .join(Sku, StockTxn.sku_id == Sku.id)
        .join(Location, StockTxn.location_id == Location.id)
    )
    if sku_code:
        stmt = stmt.where(Sku.sku_code.ilike(f"%{sku_code}%"))
    if txn_type:
        stmt = stmt.where(StockTxn.txn_type == txn_type)
    if source:
        stmt = stmt.where(StockTxn.source == source)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(StockTxn.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    items = [
        StockTxnItem(
            id=txn.id,
            txn_no=txn.txn_no,
            txn_type=txn.txn_type,
            sku_id=txn.sku_id,
            sku_code=sku.sku_code,
            location_code=loc.location_code,
            batch_no=txn.batch_no,
            expiry_date=txn.expiry_date,
            on_hand_delta=float(txn.on_hand_delta),
            allocated_delta=float(txn.allocated_delta),
            before_on_hand=float(txn.before_on_hand),
            after_on_hand=float(txn.after_on_hand),
            ref_type=txn.ref_type,
            ref_id=txn.ref_id,
            source=txn.source,
            agent_run_id=txn.agent_run_id,
            operator_id=txn.operator_id,
            remark=txn.remark,
            created_at=txn.created_at,
        )
        for txn, sku, loc in rows
    ]
    return StockTxnListResponse(
        items=items, meta=PageMeta(total=total, page=page, page_size=page_size)
    )


@router.get("/inventory/recon", response_model=ReconResponse, summary="对账视图查询")
async def get_recon(
    recon_status: str | None = None,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReconResponse:
    """对账视图查询。需 MANAGER 及以上。"""
    if current["role"] not in ("MANAGER", "ADMIN"):
        raise HTTPException(status_code=403, detail="需要仓管主管及以上权限")

    sql = "select * from v_inventory_recon"
    if recon_status:
        sql += " where recon_status = :st"
    result = await session.execute(text(sql), {"st": recon_status} if recon_status else {})
    rows = result.mappings().all()

    items = [
        ReconItem(
            sku_id=r["sku_id"],
            location_id=r["location_id"],
            batch_no=r["batch_no"],
            expiry_date=r["expiry_date"],
            inv_on_hand=float(r["inv_on_hand"]),
            txn_on_hand=float(r["txn_on_hand"]),
            diff_on_hand=float(r["diff_on_hand"]),
            recon_status=r["recon_status"],
        )
        for r in rows
    ]
    return ReconResponse(items=items)
