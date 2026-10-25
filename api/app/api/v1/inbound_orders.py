"""入库单 CRUD：列表 / 建单 / 详情 / 改明细 / 取消。

收货（receive）、上架（putaway）属第 3 批（走 apply_txn），本文件不含。
状态机：DRAFT → ARRIVED → RECEIVING → RECEIVED → PUTAWAY → DONE；
取消仅允许 DRAFT / ARRIVED。
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import InboundOrder, OrderLine, Sku
from app.db.session import get_session
from app.schemas import (
    InboundOrder as InboundOrderSchema,
)
from app.schemas import (
    InboundOrderCreate,
    InboundOrderDetail,
    InboundOrderListResponse,
    LineUpdate,
    PageMeta,
)
from app.schemas import (
    OrderLine as OrderLineSchema,
)

router = APIRouter(prefix="/inbound-orders", dependencies=[Depends(get_current_user)])

# 入库单允许取消的状态
_CANCELLABLE = {"DRAFT", "ARRIVED"}


def _gen_order_no(prefix: str = "IN") -> str:
    """生成订单号：前缀 + 日期 + 短随机串。"""
    return f"{prefix}-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


async def _get_order(session: AsyncSession, order_id: int) -> InboundOrder:
    order = await session.get(InboundOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="入库单不存在")
    return order


async def _get_lines(session: AsyncSession, inbound_id: int) -> list[OrderLine]:
    result = await session.execute(
        select(OrderLine, Sku)
        .join(Sku, OrderLine.sku_id == Sku.id)
        .where(OrderLine.inbound_id == inbound_id)
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


@router.get("", response_model=InboundOrderListResponse, summary="入库单列表")
async def list_inbound_orders(
    status: str | None = None,
    supplier_name: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> InboundOrderListResponse:
    stmt = select(InboundOrder)
    if status:
        stmt = stmt.where(InboundOrder.status == status)
    if supplier_name:
        stmt = stmt.where(InboundOrder.supplier_name.ilike(f"%{supplier_name}%"))

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(InboundOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [InboundOrderSchema.model_validate(o) for o in rows]
    return InboundOrderListResponse(
        items=items, meta=PageMeta(total=total, page=page, page_size=page_size)
    )


@router.post("", response_model=InboundOrderDetail, status_code=201, summary="建入库单")
async def create_inbound_order(
    body: InboundOrderCreate,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InboundOrderDetail:
    if not body.lines:
        raise HTTPException(status_code=422, detail="入库单至少需要一条明细")

    # 校验 sku 都存在
    sku_ids = {line.sku_id for line in body.lines}
    result = await session.execute(select(Sku).where(Sku.id.in_(sku_ids)))
    found = {s.id: s for s in result.scalars().all()}
    missing = sku_ids - set(found)
    if missing:
        raise HTTPException(status_code=422, detail=f"不存在的商品 ID: {sorted(missing)}")

    order = InboundOrder(
        order_no=_gen_order_no("IN"),
        order_type=body.order_type,
        supplier_name=body.supplier_name,
        status="DRAFT",
        expected_at=body.expected_at,
        remark=body.remark,
        created_by=current["id"],
    )
    session.add(order)
    await session.flush()  # 拿到 order.id

    total_expected = 0.0
    for idx, line in enumerate(body.lines, start=1):
        total_expected += line.qty_required
        session.add(
            OrderLine(
                order_type="IN",
                inbound_id=order.id,
                line_no=idx,
                sku_id=line.sku_id,
                qty_required=line.qty_required,
                status="OPEN",
            )
        )
    order.total_expected_qty = total_expected

    await session.commit()
    await session.refresh(order)

    lines = await _get_lines(session, order.id)
    return InboundOrderDetail(
        **InboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


@router.get("/{order_id}", response_model=InboundOrderDetail, summary="入库单详情")
async def get_inbound_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
) -> InboundOrderDetail:
    order = await _get_order(session, order_id)
    lines = await _get_lines(session, order.id)
    return InboundOrderDetail(
        **InboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


@router.patch(
    "/{order_id}/lines/{line_id}", response_model=OrderLineSchema, summary="改明细数量（仅 DRAFT）"
)
async def update_inbound_line(
    order_id: int,
    line_id: int,
    body: LineUpdate,
    session: AsyncSession = Depends(get_session),
) -> OrderLineSchema:
    order = await _get_order(session, order_id)
    if order.status != "DRAFT":
        raise HTTPException(status_code=409, detail="只有草稿状态的入库单才能改明细")

    line = await session.get(OrderLine, line_id)
    if line is None or line.inbound_id != order_id:
        raise HTTPException(status_code=404, detail="明细不存在")

    if body.qty_required <= 0:
        raise HTTPException(status_code=422, detail="数量必须大于 0")

    # 更新单行数量，并同步头部的 expected 汇总
    delta = body.qty_required - float(line.qty_required)
    line.qty_required = body.qty_required
    order.total_expected_qty = float(order.total_expected_qty) + delta

    await session.commit()

    sku = await session.get(Sku, line.sku_id)
    return _to_line_schema(line, sku)


@router.post("/{order_id}/cancel", response_model=InboundOrderDetail, summary="取消入库单")
async def cancel_inbound_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
) -> InboundOrderDetail:
    order = await _get_order(session, order_id)
    if order.status not in _CANCELLABLE:
        raise HTTPException(status_code=409, detail=f"状态 {order.status} 不允许取消")

    order.status = "CANCELLED"
    await session.commit()
    await session.refresh(order)

    lines = await _get_lines(session, order.id)
    return InboundOrderDetail(
        **InboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )
