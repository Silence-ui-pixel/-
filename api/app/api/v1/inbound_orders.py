"""入库单：CRUD + 收货 + 上架。

状态机（数据库 CHECK 约束一致）：
    DRAFT → ARRIVED → RECEIVING → RECEIVED → PUTAWAY → DONE
    取消仅允许 DRAFT / ARRIVED

作业与库存的对应关系（都走 stock_service.apply_txn，绝不直接改 inventory）：
    收货 RECEIPT      货进 RECEIVING 暂存位，on_hand += 实收
    上架 TRANSFER_OUT + PUTAWAY
                      从 RECEIVING 移出、落到 STORAGE 存储位，两条流水同一事务

为什么上架要写两条流水而不是一条：
    库存余额是「按库位」记的。一次移库必然有一条出、一条进。
    只写一条会让暂存位的账一直虚增（货已经走了但账上还挂着），
    几天后对账视图就会报 MISMATCH。
"""

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, InvalidStatusTransition
from app.core.security import get_current_user, require_role
from app.db.models import SENTINEL_EXPIRY, InboundOrder, Location, OrderLine, Sku, StockTxn
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
    PutawayRequest,
    ReceiveRequest,
)
from app.schemas import (
    OrderLine as OrderLineSchema,
)
from app.services.location_service import get_receiving_location, pick_putaway_target
from app.services.stock_service import apply_txn

router = APIRouter(prefix="/inbound-orders", dependencies=[Depends(get_current_user)])

# 入库单允许取消的状态
_CANCELLABLE = {"DRAFT", "ARRIVED"}
# 允许收货的状态
_RECEIVABLE = {"DRAFT", "ARRIVED", "RECEIVING"}
# 允许上架的状态
_PUTAWAYABLE = {"RECEIVING", "RECEIVED"}


def _source_of(agent_run_id: str | None) -> str:
    """流水来源：带 Agent 治理头就记 AGENT，否则记 WEB。

    这是审计链的起点 —— 以后能回答「这笔库存变动是人点的还是 Agent 建议的」。
    """
    return "AGENT" if agent_run_id else "WEB"


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
    current: dict = Depends(require_role("MANAGER", "ADMIN")),
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


@router.post("/{order_id}/cancel", response_model=InboundOrderDetail, summary="取消入库单（需 MANAGER/ADMIN）")
async def cancel_inbound_order(
    order_id: int,
    current: dict = Depends(require_role("MANAGER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
) -> InboundOrderDetail:
    order = await _get_order(session, order_id)
    if order.status not in _CANCELLABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="取消入库单",
            allowed_statuses=sorted(_CANCELLABLE),
        )

    order.status = "CANCELLED"
    await session.commit()
    await session.refresh(order)

    lines = await _get_lines(session, order.id)
    return InboundOrderDetail(
        **InboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


# ---------------------------------------------------------------------------
# 核心作业：收货
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/receive",
    response_model=InboundOrderDetail,
    summary="收货（写暂存位，走 apply_txn RECEIPT）",
)
async def receive_inbound_order(
    order_id: int,
    body: ReceiveRequest,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> InboundOrderDetail:
    """收货：实物进仓库，记到 RECEIVING 暂存位。

    设计要点：
    1. 货进「暂存位」而不是直接进存储位 —— 因为还没上架，位置未定。
       但账上必须有它，否则「仓库里有一堆货，系统说没有」，这是最典型的账实不符。
    2. 支持分次收货（一车货分两批到是真实场景）：
       - 明细实收量累加，收满（>= qty_required）才置 DONE，否则 PARTIAL
       - 单头全部明细收满才置 RECEIVED，否则 RECEIVING（可继续收）
    3. 允许超收（供应商多发）。schema 的 ck_line_out_qty 明确只约束出库超拣，
       入库超收是真实业务场景，拦掉会让作业员没法录真实数量。

    幂等：txn_no = RECEIPT-{order_id}-{line_id}-{seq}，seq 是该明细已有
    收货流水数 + 1。同一批次自然唯一，同一次请求重放时 seq 相同、命中幂等。
    Idempotency-Key 头用于挡住 PDA 弱网重试造成的重复请求。
    """
    order = await _get_order(session, order_id)
    if order.status not in _RECEIVABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="收货",
            allowed_statuses=sorted(_RECEIVABLE),
        )

    # 明细必须属于本单，否则可能被用来改别的单
    all_lines = {line.id: (line, sku) for line, sku in await _get_lines(session, order.id)}
    if not body.lines:
        raise HTTPException(status_code=422, detail="收货明细不能为空")

    receiving = await get_receiving_location(session)
    now = datetime.now(UTC)
    total_received = 0.0
    all_done = True

    for item in body.lines:
        pair = all_lines.get(item.line_id)
        if pair is None:
            raise HTTPException(
                status_code=422,
                detail=f"明细 {item.line_id} 不属于本入库单",
            )
        line, sku = pair

        if item.qty_actual < 0:
            raise HTTPException(status_code=422, detail="实收数量不能为负数")
        if item.qty_rejected < 0:
            raise HTTPException(status_code=422, detail="不良数量不能为负数")

        # 批次管理商品必须给批次号，否则批次追溯直接断链
        batch_no = (item.batch_no or "").strip()
        if sku.is_batch_managed and not batch_no:
            raise HTTPException(
                status_code=422,
                detail=f"商品 {sku.sku_code} 是批次管理商品，收货必须提供批次号",
            )

        expiry = item.expiry_date or SENTINEL_EXPIRY
        qty_in = float(item.qty_actual)

        if qty_in > 0:
            # 序号 = 该明细已有 RECEIPT 流水数 + 1，保证分次收货 txn_no 唯一
            seq = (
                await session.execute(
                    select(func.count())
                    .select_from(StockTxn)
                    .where(
                        StockTxn.ref_type == "INBOUND",
                        StockTxn.ref_id == order.id,
                        StockTxn.ref_line_id == line.id,
                        StockTxn.txn_type == "RECEIPT",
                    )
                )
            ).scalar_one()
            await apply_txn(
                session,
                txn_no=f"RECEIPT-{order.id}-{line.id}-{seq + 1}",
                txn_type="RECEIPT",
                sku_id=line.sku_id,
                location_id=receiving.id,
                batch_no=batch_no,
                expiry_date=expiry,
                on_hand_delta=qty_in,
                ref_type="INBOUND",
                ref_id=order.id,
                ref_line_id=line.id,
                source=_source_of(agent_run_id),
                operator_id=current["id"],
                agent_run_id=agent_run_id,
                remark=f"收货 {order.order_no}",
            )

        # 实收量累加（分次收货），不良量覆盖为本次值
        line.qty_actual = float(line.qty_actual or 0) + qty_in
        line.qty_rejected = float(item.qty_rejected or 0)
        line.batch_no = batch_no
        line.expiry_date = expiry
        # 收满才算 DONE；没收满且本次收了货则 PARTIAL（可继续收）
        # 实收为 0 且从未收过货，供应商没发这一项，直接 CANCELLED 避免卡流程
        if line.qty_actual >= float(line.qty_required):
            line.status = "DONE"
        elif qty_in > 0 or line.qty_actual > 0:
            line.status = "PARTIAL"
        else:
            line.status = "CANCELLED"

        total_received += qty_in
        if line.status != "DONE":
            all_done = False

    order.total_received_qty = float(order.total_received_qty or 0) + total_received
    order.received_at = now
    # 全部明细收满才完结，否则留在 RECEIVING 等待下一批到货
    order.status = "RECEIVED" if all_done else "RECEIVING"
    order.version = (order.version or 0) + 1

    try:
        await session.commit()
    except DomainError:
        await session.rollback()
        raise

    await session.refresh(order)
    lines = await _get_lines(session, order.id)
    return InboundOrderDetail(
        **InboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )


# ---------------------------------------------------------------------------
# 核心作业：上架
# ---------------------------------------------------------------------------
@router.post(
    "/{order_id}/putaway",
    response_model=InboundOrderDetail,
    summary="上架（走 apply_txn PUTAWAY）",
)
async def putaway_inbound_order(
    order_id: int,
    body: PutawayRequest,
    current: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    agent_run_id: str | None = Header(default=None, alias="X-Agent-Run-Id"),
) -> InboundOrderDetail:
    """上架：把已收货的货从暂存位移到存储位。

    一次移库写两条流水（同一事务）：
        RECEIVING 位  TRANSFER_OUT  on_hand -= 数量
        目标存储位    PUTAWAY       on_hand += 数量

    为什么要两条：库存余额按库位记。只写出、不写进，货就在账上消失了；
    只写进、不写出，暂存位会一直虚增。两种都会让对账视图报异常。

    目标位：body 里指定优先；没指定就按 location_service 的策略自动选
    （优先合并到已有同 SKU 的存储位，减少碎片）。
    """
    order = await _get_order(session, order_id)
    if order.status not in _PUTAWAYABLE:
        raise InvalidStatusTransition(
            order_no=order.order_no,
            current_status=order.status,
            action="上架",
            allowed_statuses=sorted(_PUTAWAYABLE),
        )

    all_lines = {line.id: (line, sku) for line, sku in await _get_lines(session, order.id)}
    receiving = await get_receiving_location(session)

    # 未指定明细时，处理所有「已收货但未指定目标位」的行
    requested: dict[int, int | None] = {}
    if body.lines:
        for item in body.lines:
            if item.line_id not in all_lines:
                raise HTTPException(
                    status_code=422, detail=f"明细 {item.line_id} 不属于本入库单"
                )
            requested[item.line_id] = item.to_location_id
    else:
        requested = {
            line.id: None
            for line, _sku in all_lines.values()
            if float(line.qty_actual) > 0 and line.to_location_id is None
        }

    for line_id, explicit_target in requested.items():
        line, _sku = all_lines[line_id]
        qty = float(line.qty_actual)
        if qty <= 0:
            continue
        if line.to_location_id is not None:
            # 已经上架过，跳过（幂等：重复请求不会重复移库）
            continue

        if explicit_target is not None:
            target = await session.get(Location, explicit_target)
            if target is None:
                raise HTTPException(status_code=422, detail=f"目标库位 {explicit_target} 不存在")
            if target.location_type != "STORAGE":
                raise HTTPException(
                    status_code=422,
                    detail=f"目标库位 {target.location_code} 不是存储位，不能上架到该处",
                )
        else:
            target = await pick_putaway_target(
                session, sku_id=line.sku_id, exclude_location_id=receiving.id
            )

        # 1) 从暂存位移出（同一维度：sku + 批次 + 效期）
        await apply_txn(
            session,
            txn_no=f"PUTAWAY-OUT-{order.id}-{line.id}",
            txn_type="TRANSFER_OUT",
            sku_id=line.sku_id,
            location_id=receiving.id,
            batch_no=line.batch_no,
            expiry_date=line.expiry_date,
            on_hand_delta=-qty,
            ref_type="INBOUND",
            ref_id=order.id,
            ref_line_id=line.id,
            source=_source_of(agent_run_id),
            operator_id=current["id"],
            agent_run_id=agent_run_id,
            remark=f"上架移出 {order.order_no}",
        )
        # 2) 落到存储位
        await apply_txn(
            session,
            txn_no=f"PUTAWAY-IN-{order.id}-{line.id}",
            txn_type="PUTAWAY",
            sku_id=line.sku_id,
            location_id=target.id,
            batch_no=line.batch_no,
            expiry_date=line.expiry_date,
            on_hand_delta=qty,
            ref_type="INBOUND",
            ref_id=order.id,
            ref_line_id=line.id,
            source=_source_of(agent_run_id),
            operator_id=current["id"],
            agent_run_id=agent_run_id,
            remark=f"上架到 {target.location_code}",
        )

        line.to_location_id = target.id
        line.status = "DONE"

    # 全单所有已收明细都上架完 → DONE；否则 PUTAWAY（还在进行中）
    pending = [
        line
        for line, _sku in all_lines.values()
        if float(line.qty_actual) > 0 and line.to_location_id is None
    ]
    order.status = "DONE" if not pending else "PUTAWAY"
    order.version = (order.version or 0) + 1

    try:
        await session.commit()
    except DomainError:
        await session.rollback()
        raise

    await session.refresh(order)
    lines = await _get_lines(session, order.id)
    return InboundOrderDetail(
        **InboundOrderSchema.model_validate(order).model_dump(),
        lines=[_to_line_schema(line, sku) for line, sku in lines],
    )
