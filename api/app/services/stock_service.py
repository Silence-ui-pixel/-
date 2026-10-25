"""库存写入口 —— 全系统唯一的库存变动通道。

三条铁律（继承自 schema.sql）：
  1) 库存只能通过 apply_txn 写入，禁止任何地方直接 UPDATE inventory
  2) 每次变动在同一事务内写一条 stock_txn（带 before/after 快照）
  3) stock_txn 只追加（数据库触发器强制）

apply_txn 五步（必须同一事务）：
  1. SELECT ... FOR UPDATE 锁住 inventory 行（按唯一维度）
  2. 查幂等：txn_no 已存在则直接返回原记录
  3. 校验：出库/分配场景可用量 >= 需求，否则抛 INVENTORY_INSUFFICIENT
  4. 写 inventory（更新 qty_on_hand / qty_allocated，version+1）
  5. 写 stock_txn（before/after 快照 + 两个 delta），提交

关键约束：
  - before/after 快照由服务端在锁内现算，绝不信任入参
  - 首次入库（inventory 行不存在）自动 INSERT
  - 幂等查询放在锁之后，防止两个并发同 txn_no 双写
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InventoryInsufficient
from app.db.models import Inventory, StockTxn


async def apply_txn(
    session: AsyncSession,
    *,
    txn_no: str,
    txn_type: str,
    sku_id: int,
    location_id: int,
    batch_no: str = "",
    expiry_date: date = date.max,
    on_hand_delta: float = 0,
    allocated_delta: float = 0,
    ref_type: str | None = None,
    ref_id: int | None = None,
    ref_line_id: int | None = None,
    source: str = "SYSTEM",
    operator_id: int | None = None,
    agent_run_id: str | None = None,
    remark: str | None = None,
) -> StockTxn:
    """对库存维度执行一次变动，落余额 + 流水，返回 StockTxn。

    on_hand_delta:  现有量变化（入库 +，出库 -，纯分配 0）
    allocated_delta: 分配量变化（分配 +，拣货/取消分配 -，纯出库 0）

    调用方负责事务边界（commit/rollback）——本函数只做业务逻辑，
    不 commit。这样上层可以把多个 apply_txn 包进同一个事务。
    """
    # 1. 锁行（无行可锁时，出库需拦截；入库走 upsert）
    stmt = (
        select(Inventory)
        .where(
            Inventory.sku_id == sku_id,
            Inventory.location_id == location_id,
            Inventory.batch_no == batch_no,
            Inventory.expiry_date == expiry_date,
        )
        .with_for_update()
    )
    inv = (await session.execute(stmt)).scalar_one_or_none()

    # 2. 幂等：锁后先查 txn_no，命中直接返回，不等唯一约束抛错
    existing = (
        await session.execute(select(StockTxn).where(StockTxn.txn_no == txn_no))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # 3. 计算 before 快照
    before_on_hand = float(inv.qty_on_hand) if inv is not None else 0.0
    before_allocated = float(inv.qty_allocated) if inv is not None else 0.0

    # 4. 校验可用量（仅当本次是「扣减现有量」或「增加分配量」时需要）
    #    可用量 = 现有量 - 已分配量
    need_on_hand = max(0.0, -on_hand_delta)          # 出库/扣减的量
    need_allocated = max(0.0, allocated_delta)       # 分配要锁定的量
    available = before_on_hand - before_allocated    # 当前可用量

    if need_on_hand > 0 and need_on_hand > available:
        raise InventoryInsufficient(
            sku_code=await _sku_code_of(session, sku_id),
            batch_no=batch_no,
            required=need_on_hand,
            available=available,
        )
    if need_allocated > 0 and need_allocated > available:
        raise InventoryInsufficient(
            sku_code=await _sku_code_of(session, sku_id),
            batch_no=batch_no,
            required=need_allocated,
            available=available,
        )

    # 5. 写 inventory（upsert：首次入库自动建行）
    after_on_hand = before_on_hand + on_hand_delta
    after_allocated = before_allocated + allocated_delta

    if inv is None:
        # 首次入库，且必须是「净入库」方向（否则应早被拦截）
        inv = Inventory(
            sku_id=sku_id,
            location_id=location_id,
            batch_no=batch_no,
            expiry_date=expiry_date,
            qty_on_hand=after_on_hand,
            qty_allocated=after_allocated,
            version=1,
        )
        session.add(inv)
    else:
        inv.qty_on_hand = after_on_hand
        inv.qty_allocated = after_allocated
        inv.version = (inv.version or 0) + 1

    # 6. 写流水（before/after 快照自洽，DB 有 CHECK 兜底）
    txn = StockTxn(
        txn_no=txn_no,
        txn_type=txn_type,
        sku_id=sku_id,
        location_id=location_id,
        batch_no=batch_no,
        expiry_date=expiry_date,
        on_hand_delta=on_hand_delta,
        allocated_delta=allocated_delta,
        before_on_hand=before_on_hand,
        after_on_hand=after_on_hand,
        ref_type=ref_type,
        ref_id=ref_id,
        ref_line_id=ref_line_id,
        source=source,
        agent_run_id=agent_run_id,
        operator_id=operator_id,
        remark=remark,
    )
    session.add(txn)
    # flush 让 txn.id 生成（不 commit，事务由调用方控制）
    await session.flush()
    return txn


async def _sku_code_of(session: AsyncSession, sku_id: int) -> str:
    """取 SKU 编码，用于异常 detail。失败时返回占位，不影响主流程。"""
    from app.db.models import Sku

    sku = await session.get(Sku, sku_id)
    return sku.sku_code if sku else str(sku_id)
