"""出库单 CRUD：列表 / 建单 / 详情 / 取消。

分配（allocate）、拣货（pick）、发运（ship）属第 3 批（走 apply_txn），本文件不含。
状态机：DRAFT → ALLOCATED → PICKING → PICKED → SHIPPED；
取消仅允许 DRAFT / ALLOCATED（ALLOCATED 的 DEALLOCATE 回滚属第 3 批）。
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import OrderLine, OutboundOrder, Sku
from app.db.session import get_session
from app.schemas import (
    OrderLine as OrderLineSchema,
)
from app.schemas import (
    OutboundOrder as OutboundOrderSchema,
)
from app.schemas import (
    OutboundOrderCreate,
    OutboundOrderDetail,
    OutboundOrderListResponse,
    PageMeta,
)

router = APIRouter(prefix="/outbound-orders", dependencies=[Depends(get_current_user)])

# 出库单允许取消的状态（第 2 批只做状态翻转，不碰库存）
_CANCELLABLE = {"DRAFT", "ALLOCATED"}


def _gen_order_no() -> str:
    return f"OUT-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


async def _get_order(session: AsyncSession, order_id: int) -> OutboundOrder:
    order = await session.get(OutboundOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="出库单不存在")
    return order


async def _get_lines(session: AsyncSession, outbound_id: int) -> list[tuple[OrderLine, Sku]]:
    result = await session.execute(
        select(OrderLine, Sku)
        .join(Sku, OrderLine.sku_id == Sku.id)
        .where(OrderLine.outbound_id == outbound_id)
        .order_by(OrderLine.line_no)
    )
    return [(line, sku) for line, sku in result.all()]


def _to_line_schema(line: OrderLine, sku: Sku) -> OrderLineSchema:
    return OrderLineSchema(
        id=line.id,
        line_no=line.line_no,
        sku_id=line.sku_id,
        sku_code=sku.sku_code,
        sku_name=sku.name,
        qty_required=float(line.qty_required),
        qty_actual=float(line.qty_actual),
        qty_rejected=float(line.qty_rejected),
        batch_no=line.batch_no,
        expiry_date=line.expiry_date,
        from_location_id=line.from_location_id,
        to_location_id=line.to_location_id,
        status=line.status,
    )


@router.get("", response_model=OutboundOrderListResponse, summary="出库单列表")
async def list_outbound_orders(
    status: str | None = None,
    customer_name: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> OutboundOrderListResponse:
    stmt = select(OutboundOrder)
    if status:
        stmt = stmt.where(OutboundOrder.status == status)
    if customer_name:
        stmt = stmt.where(OutboundOrder.customer_name.ilike(f"%{customer_name}%"))

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(OutboundOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [OutboundOrderSchema.model_validate(o) for o in rows]
    return OutboundOrderListResponse(
        items=items, meta=PageMeta(total=total, page=page, page_size=page_size)
    )


@router.post("", response_model=OutboundOrderDetail, status_code=201, summary="建出库单")
async def create_outbound_order(
    body: OutboundOrderCreate,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OutboundOrderDetail:
    if not body.lines:
        raise HTTPException(status_code=422, detail="出库单至少需要一条明细")

    sku_ids = {line.sku_id for line in body.lines}
    result = await session.execute(select(Sku).where(Sku.id.in_(sku_ids)))
    found = {s.id for s in result.scalars().all()}
    missing = sku_ids - found
    if missing:
        raise HTTPException(status_code=422, detail=f"不存在的商品 ID: {sorted(missing)}")

    order = OutboundOrder(
        order_no=_gen_order_no(),
        order_type=body.order_type,
        customer_name=body.customer_name,
        status="DRAFT",
        priority=body.priority,
        requested_ship_at=body.requested_ship_at,
        remark=body.remark,
        created_by=current["id"],
    )
    session.add(order)
    await session.flush()

    total_qty = 0.0
    for idx, line in enumerate(body.lines, start=1):
        total_qty += line.qty_required
        session.add(
            OrderLine(
                order_type="OUT",
                outbound_id=order.id,
                line_no=idx,
                sku_id=line.sku_id,
                qty_required=line.qty_required,
                status="OPEN",
            )
        )
    order.total_qty = total_qty

    await session.commit()
    await session.refresh(order)

    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


@router.get("/{order_id}", response_model=OutboundOrderDetail, summary="出库单详情")
async def get_outbound_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
) -> OutboundOrderDetail:
    order = await _get_order(session, order_id)
    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


@router.post("/{order_id}/cancel", response_model=OutboundOrderDetail, summary="取消出库单")
async def cancel_outbound_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
) -> OutboundOrderDetail:
    order = await _get_order(session, order_id)
    if order.status not in _CANCELLABLE:
        raise HTTPException(status_code=409, detail=f"状态 {order.status} 不允许取消")

    # 第 2 批：仅翻转状态。ALLOCATED 的 DEALLOCATE 库存回滚属第 3 批（走 apply_txn）。
    order.status = "CANCELLED"
    await session.commit()
    await session.refresh(order)

    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )
