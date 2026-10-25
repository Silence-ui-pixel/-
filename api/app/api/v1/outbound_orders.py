"""出库单：CRUD + 分配 + 拣货 + 发运。

状态机（数据库 CHECK 约束一致）：
    DRAFT → ALLOCATED → PICKING → PICKED → SHIPPED
    取消允许 DRAFT / ALLOCATED

作业与库存的对应关系（都走 stock_service.apply_txn，绝不直接改 inventory）：
    分配 ALLOCATE       allocated += 数量（只锁定，货不动，on_hand 不变）
    拣货 PICK           STORAGE 位 on_hand -= 数量 且 allocated -= 数量；
                        STAGING 位（发货暂存）on_hand += 数量
    发运 SHIP           STAGING 位 on_hand -= 数量（真正出库）
    取消 DEALLOCATE     allocated -= 数量（把锁定的库存放回去）

为什么拣货要记到 STAGING 而不是让货从账上消失：
    拣出来到发运之间，货物理上还在仓库（发货区）。如果账上直接扣掉，
    这段时间的账实就是不符的；一旦客户取消或发错货，根本查不到货在哪。
    记到 STAGING 让账实始终一致，也符合 schema 里预留 STAGING 类型的意图。

为什么分配只动 allocated：
    on_hand 是「仓库里实际有多少」，货还在架上，不能变。
    allocated 是「已经许给别人多少」。可用量 = on_hand - allocated，
    这个生成列就是防止两个订单抢同一批货的关键。
"""

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, InvalidStatusTransition, InventoryInsufficient
from app.core.security import get_current_user, require_role
from app.db.models import Location, OrderLine, OutboundOrder, Sku
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
    PickConfirmRequest,
    PickLine,
    PickPlanResponse,
    ShipRequest,
)
from app.services.allocation_service import find_fefo_allocation
from app.services.location_service import get_staging_location
from app.services.stock_service import apply_txn

router = APIRouter(prefix="/outbound-orders", dependencies=[Depends(get_current_user)])

# 允许取消的状态（ALLOCATED 取消时要把锁定的库存放回去）
_CANCELLABLE = {"DRAFT", "ALLOCATED"}
# 允许分配的状态
_ALLOCATABLE = {"DRAFT"}
# 允许拣货的状态
_PICKABLE = {"ALLOCATED", "PICKING"}
# 允许发运的状态
_SHIPPABLE = {"PICKED"}


def _source_of(agent_run_id: str | None) -> str:
    return "AGENT" if agent_run_id else "WEB"


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


@router.post("/{order_id}/cancel", response_model=OutboundOrderDetail, summary="取消出库单（需 MANAGER/ADMIN）")
async def cancel_outbound_order(
    order_id: int,
    current: dict = Depends(require_role("MANAGER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> OutboundOrderDetail:
    """取消出库单。

    DRAFT 直接取消；ALLOCATED 必须先 DEALLOCATE 把锁定的库存放回去，
    否则那批货会被永久锁住 —— 账面显示「已分配」，但没有任何订单会来取，
    可用量永远少一块，只能靠人工改库才能恢复。这是很隐蔽的库存泄漏。
    """
    order = await _get_order(session, order_id)
    if order.status not in _CANCELLABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="取消出库单",
            allowed_statuses=sorted(_CANCELLABLE),
        )

    if order.status == "ALLOCATED":
        all_lines = await _get_lines(session, order.id)
        for line, _sku in all_lines:
            locked = float(line.qty_required)
            if locked <= 0 or line.from_location_id is None:
                continue
            await apply_txn(
                session,
                txn_no=f"DEALLOCATE-{order.id}-{line.id}",
                txn_type="DEALLOCATE",
                sku_id=line.sku_id,
                location_id=line.from_location_id,
                batch_no=line.batch_no,
                expiry_date=line.expiry_date,
                allocated_delta=-locked,
                ref_type="OUTBOUND",
                ref_id=order.id,
                ref_line_id=line.id,
                source=_source_of(agent_run_id),
                operator_id=current["id"],
                agent_run_id=agent_run_id,
                remark=f"取消出库单解锁 {order.order_no}",
            )
            line.status = "CANCELLED"

    order.status = "CANCELLED"
    order.version = (order.version or 0) + 1

    try:
        await session.commit()
    except DomainError:
        await session.rollback()
        raise

    await session.refresh(order)
    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


# ---------------------------------------------------------------------------
# 核心作业：分配库存
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/allocate",
    response_model=OutboundOrderDetail,
    summary="分配库存（按明细行 FEFO 锁批次，只动 allocated_delta）",
)
async def allocate_outbound_order(
    order_id: int,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> OutboundOrderDetail:
    """分配库存：把货「许给」这张单，但不从架上拿走。

    全批一起成功或一起失败 —— 只要有一条明细库存不足，整体回滚。
    半分配状态是最难处理的：单子看起来在推进，实际发不出货，
    仓库现场和系统状态会彻底对不上。

    Sprint 1 限制：一条明细只能绑一个批次/库位。单批次不够就报 409，
    detail 里带 max_available，前端可据此提示「拆成多行」。
    跨批次分配需要独立的 allocation 明细表，属 Sprint 2。
    """
    order = await _get_order(session, order_id)
    if order.status not in _ALLOCATABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="分配库存",
            allowed_statuses=sorted(_ALLOCATABLE),
        )

    all_lines = await _get_lines(session, order.id)
    if not all_lines:
        raise HTTPException(status_code=422, detail="出库单没有明细，无法分配")

    for line, sku in all_lines:
        if line.status not in ("OPEN", "ALLOCATED"):
            continue
        need = float(line.qty_required)
        result = await find_fefo_allocation(
            session, sku_id=line.sku_id, qty_required=need
        )
        if not result.ok:
            # 注意顺序：先把要用的值取出来，再 rollback。
            # rollback 会让 session 里的 ORM 对象全部 expire，之后访问
            # sku.sku_code 会触发隐式的同步 refresh，在异步 session 里直接
            # 抛 MissingGreenlet —— 这个坑只有在「先 rollback 再读字段」时才会踩到。
            sku_code = sku.sku_code
            order_no = order.order_no
            line_no = line.line_no
            await session.rollback()
            raise InventoryInsufficient(
                sku_code=sku_code,
                batch_no="",
                required=need,
                available=result.max_available,
                extra={
                    "order_no": order_no,
                    "line_no": line_no,
                    "note": "单批次可用量不足；Sprint 1 不支持跨批次分配，请拆分该明细",
                },
            )

        await apply_txn(
            session,
            txn_no=f"ALLOCATE-{order.id}-{line.id}",
            txn_type="ALLOCATE",
            sku_id=line.sku_id,
            location_id=result.location.id,
            batch_no=result.inv.batch_no,
            expiry_date=result.inv.expiry_date,
            allocated_delta=need,
            ref_type="OUTBOUND",
            ref_id=order.id,
            ref_line_id=line.id,
            source=_source_of(agent_run_id),
            operator_id=current["id"],
            agent_run_id=agent_run_id,
            remark=f"分配 {order.order_no}",
        )

        line.from_location_id = result.location.id
        line.batch_no = result.inv.batch_no
        line.expiry_date = result.inv.expiry_date
        line.status = "ALLOCATED"

    order.status = "ALLOCATED"
    order.version = (order.version or 0) + 1

    try:
        await session.commit()
    except DomainError:
        await session.rollback()
        raise

    await session.refresh(order)
    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


# ---------------------------------------------------------------------------
# 核心作业：拣货
# ---------------------------------------------------------------------------
@router.get(
    "/{order_id}/pick",
    response_model=PickPlanResponse,
    summary="获取拣货路径（按 pick_seq 排序）",
)
async def get_pick_plan(
    order_id: int,
    session: AsyncSession = Depends(get_session),
) -> PickPlanResponse:
    """拣货路径：按库位拣货顺序排，避免作业员在仓库里来回折返。

    这不是锦上添花 —— 一个 20 行的单子，路径没排序可能多走 15 分钟。
    """
    order = await _get_order(session, order_id)
    if order.status not in ("ALLOCATED", "PICKING", "PICKED"):
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="获取拣货路径",
            allowed_statuses=["ALLOCATED", "PICKING", "PICKED"],
        )

    stmt = (
        select(OrderLine, Sku, Location)
        .join(Sku, OrderLine.sku_id == Sku.id)
        .outerjoin(Location, OrderLine.from_location_id == Location.id)
        .where(OrderLine.outbound_id == order.id)
        .order_by(
            Location.pick_seq.asc().nulls_last(),
            Location.id.asc().nulls_last(),
            OrderLine.line_no.asc(),
        )
    )
    rows = (await session.execute(stmt)).all()

    return PickPlanResponse(
        lines=[
            PickLine(
                line_id=line.id,
                sku_id=line.sku_id,
                sku_code=sku.sku_code,
                sku_name=sku.name,
                location_id=line.from_location_id,
                location_code=loc.location_code if loc else "",
                qty_required=float(line.qty_required),
                batch_no=line.batch_no,
                expiry_date=line.expiry_date,
            )
            for line, sku, loc in rows
        ]
    )


@router.post(
    "/{order_id}/pick",
    response_model=OutboundOrderDetail,
    summary="拣货确认（走 apply_txn PICK）",
)
async def pick_outbound_order(
    order_id: int,
    body: PickConfirmRequest,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> OutboundOrderDetail:
    """拣货确认：货从存储位拣出，放到发货暂存位（STAGING）。

    每条明细写两条流水：
        存储位   PICK         on_hand -= 实拣；allocated -= 应拣（全额解锁）
        STAGING  TRANSFER_IN  on_hand += 实拣

    为什么 allocated 按「应拣」减而不是「实拣」：
        分配时锁定的是应拣量。短拣意味着剩下的货放回去了，锁定必须全额解开，
        否则那部分库存会永久卡在「已分配」状态，谁都分配不到。
    """
    order = await _get_order(session, order_id)
    if order.status not in _PICKABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="拣货",
            allowed_statuses=sorted(_PICKABLE),
        )

    if not body.lines:
        raise HTTPException(status_code=422, detail="拣货明细不能为空")

    all_lines = {line.id: (line, sku) for line, sku in await _get_lines(session, order.id)}
    staging = await get_staging_location(session)
    picked_total = 0.0

    for item in body.lines:
        pair = all_lines.get(item.line_id)
        if pair is None:
            raise HTTPException(status_code=422, detail=f"明细 {item.line_id} 不属于本出库单")
        line, _sku = pair

        if item.qty_actual < 0:
            raise HTTPException(status_code=422, detail="实拣数量不能为负数")
        if float(item.qty_actual) > float(line.qty_required) + 1e-6:
            raise HTTPException(
                status_code=422,
                detail=f"明细 {line.line_no} 实拣 {item.qty_actual} 超过应拣 {line.qty_required}",
            )
        if line.from_location_id is None:
            raise HTTPException(
                status_code=409, detail=f"明细 {line.line_no} 尚未分配库位，不能拣货"
            )

        qty_pick = float(item.qty_actual)
        locked = float(line.qty_required)

        if qty_pick > 0:
            await apply_txn(
                session,
                txn_no=f"PICK-{order.id}-{line.id}",
                txn_type="PICK",
                sku_id=line.sku_id,
                location_id=line.from_location_id,
                batch_no=line.batch_no,
                expiry_date=line.expiry_date,
                on_hand_delta=-qty_pick,
                allocated_delta=-locked,
                ref_type="OUTBOUND",
                ref_id=order.id,
                ref_line_id=line.id,
                source=_source_of(agent_run_id),
                operator_id=current["id"],
                agent_run_id=agent_run_id,
                remark=f"拣货 {order.order_no}",
            )
            await apply_txn(
                session,
                txn_no=f"PICK-STAGE-{order.id}-{line.id}",
                txn_type="TRANSFER_IN",
                sku_id=line.sku_id,
                location_id=staging.id,
                batch_no=line.batch_no,
                expiry_date=line.expiry_date,
                on_hand_delta=qty_pick,
                ref_type="OUTBOUND",
                ref_id=order.id,
                ref_line_id=line.id,
                source=_source_of(agent_run_id),
                operator_id=current["id"],
                agent_run_id=agent_run_id,
                remark=f"拣货入发货暂存 {order.order_no}",
            )

        line.qty_actual = qty_pick
        line.qty_rejected = float(item.qty_rejected or 0)
        line.status = "DONE" if abs(qty_pick - locked) < 1e-6 else "PARTIAL"
        picked_total += qty_pick

    order.status = "PICKED"
    order.total_qty = picked_total
    order.version = (order.version or 0) + 1

    try:
        await session.commit()
    except DomainError:
        await session.rollback()
        raise

    await session.refresh(order)
    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


# ---------------------------------------------------------------------------
# 核心作业：发运
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/ship",
    response_model=OutboundOrderDetail,
    summary="发运（扣减在途，走 apply_txn SHIP）",
)
async def ship_outbound_order(
    order_id: int,
    body: ShipRequest,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> OutboundOrderDetail:
    """发运：货真正离开仓库，从 STAGING 位扣减。

    这是「账实一致」的最后一环 —— 拣货后货还在账上（在发货区），
    发运后账上才消失。中间任何一步都可能出问题（客户取消、装错车），
    货始终在账上才查得到。
    """
    order = await _get_order(session, order_id)
    if order.status not in _SHIPPABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="发运",
            allowed_statuses=sorted(_SHIPPABLE),
        )

    all_lines = await _get_lines(session, order.id)
    staging = await get_staging_location(session)

    for line, _sku in all_lines:
        qty = float(line.qty_actual)
        if qty <= 0:
            continue
        await apply_txn(
            session,
            txn_no=f"SHIP-{order.id}-{line.id}",
            txn_type="SHIP",
            sku_id=line.sku_id,
            location_id=staging.id,
            batch_no=line.batch_no,
            expiry_date=line.expiry_date,
            on_hand_delta=-qty,
            ref_type="OUTBOUND",
            ref_id=order.id,
            ref_line_id=line.id,
            source=_source_of(agent_run_id),
            operator_id=current["id"],
            agent_run_id=agent_run_id,
            remark=f"发运 {order.order_no}",
        )

    order.status = "SHIPPED"
    order.shipped_at = datetime.now(UTC)
    if body.carrier is not None:
        order.carrier = body.carrier
    if body.tracking_no is not None:
        order.tracking_no = body.tracking_no
    order.version = (order.version or 0) + 1

    try:
        await session.commit()
    except DomainError:
        await session.rollback()
        raise

    await session.refresh(order)
    lines = await _get_lines(session, order.id)
    return OutboundOrderDetail(
        **OutboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )
