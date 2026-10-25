"""apply_txn 四个关键场景测试（S1-15b）。

对应 A_project/drafts/apply-txn-cases.md：
  TC-01 正常入库    —— 余额/流水/对账三处一致 + 首次入库自动建行
  TC-02 库存不足    —— 抛 INVENTORY_INSUFFICIENT + 零副作用
  TC-03 并发扣减    —— 双连接 + 栅栏，恰好一成一败
  TC-04 幂等        —— txn_no 重复提交只生效一次
"""

import asyncio
from datetime import date

import pytest
from sqlalchemy import func, select, text

from app.core.errors import InventoryInsufficient
from app.db.models import Inventory, StockTxn
from app.services.stock_service import apply_txn


# ---------------------------------------------------------------------------
# TC-01 正常入库
# ---------------------------------------------------------------------------
async def test_tc01_receipt(session, base_ids):
    sku_id, location_id = base_ids["sku_id"], base_ids["location_id"]

    txn = await apply_txn(
        session,
        txn_no="TC01-RECEIPT-0001",
        txn_type="RECEIPT",
        sku_id=sku_id,
        location_id=location_id,
        batch_no="B20261001",
        expiry_date=date(2027, 10, 1),
        on_hand_delta=100,
        allocated_delta=0,
        source="PDA",
    )
    await session.commit()

    # 断言 1：返回值快照
    assert float(txn.before_on_hand) == 0.0
    assert float(txn.after_on_hand) == 100.0

    # 断言 2：inventory 余额 + 生成列 available
    inv = (
        await session.execute(
            select(Inventory).where(
                Inventory.sku_id == sku_id, Inventory.location_id == location_id
            )
        )
    ).scalar_one()
    assert float(inv.qty_on_hand) == 100.0
    assert float(inv.qty_allocated) == 0.0
    # qty_available 是生成列，刷新后读取
    await session.refresh(inv)
    assert float(inv.qty_available) == 100.0

    # 断言 3：version == 1
    assert inv.version == 1

    # 断言 4：流水 1 行
    cnt = (
        await session.execute(select(func.count()).select_from(StockTxn))
    ).scalar_one()
    assert cnt == 1

    # 断言 5：对账 OK
    r = await session.execute(
        text(
            "select count(*) from v_inventory_recon where recon_status <> 'OK'"
        )
    )
    assert r.scalar_one() == 0

    # 断言 6（边界）：首次入库自动建了 inventory 行（上面已 scalar_one，即已证明存在）


# ---------------------------------------------------------------------------
# TC-02 库存不足
# ---------------------------------------------------------------------------
async def test_tc02_insufficient(session, base_ids):
    sku_id, location_id = base_ids["sku_id"], base_ids["location_id"]
    batch = "B20261002"

    # 前置：现有 50、已分配 20 → 可用 30
    await _seed_inventory(session, sku_id, location_id, batch, on_hand=50, allocated=20)
    await session.commit()

    with pytest.raises(InventoryInsufficient) as exc:
        await apply_txn(
            session,
            txn_no="TC02-SHIP-0001",
            txn_type="SHIP",
            sku_id=sku_id,
            location_id=location_id,
            batch_no=batch,
            on_hand_delta=-40,  # 需求 40 > 可用 30
            allocated_delta=0,
            source="WEB",
        )

    # 断言 1：错误码
    assert exc.value.code == "INVENTORY_INSUFFICIENT"
    # 断言 2：detail 带三数
    assert exc.value.detail["required"] == 40.0
    assert exc.value.detail["available"] == 30.0
    assert exc.value.detail["shortfall"] == 10.0

    # 断言 3：inventory 数值未变（事务已回滚，重新查）
    await session.rollback()
    inv = (
        await session.execute(
            select(Inventory).where(
                Inventory.sku_id == sku_id,
                Inventory.location_id == location_id,
                Inventory.batch_no == batch,
            )
        )
    ).scalar_one()
    assert float(inv.qty_on_hand) == 50.0
    assert float(inv.qty_allocated) == 20.0
    assert inv.version == 0  # 种子写入时 version 默认 0

    # 断言 4：无脏流水
    cnt = (
        await session.execute(select(func.count()).select_from(StockTxn))
    ).scalar_one()
    assert cnt == 0


# ---------------------------------------------------------------------------
# TC-03 并发扣减
# ---------------------------------------------------------------------------
async def test_tc03_concurrent(session, session_factory, base_ids):
    sku_id, location_id = base_ids["sku_id"], base_ids["location_id"]
    batch = "B20261003"

    # 前置：现有 10、已分配 0 → 可用 10
    await _seed_inventory(session, sku_id, location_id, batch, on_hand=10, allocated=0)
    await session.commit()

    # 两个独立 session，各扣 8（合计 16 > 可用 10）
    async def do_txn(txn_no: str):
        async with session_factory() as s:
            try:
                txn = await apply_txn(
                    s,
                    txn_no=txn_no,
                    txn_type="SHIP",
                    sku_id=sku_id,
                    location_id=location_id,
                    batch_no=batch,
                    on_hand_delta=-8,
                    allocated_delta=0,
                    source="PDA",
                )
                await s.commit()
                return ("ok", txn)
            except InventoryInsufficient as e:
                await s.rollback()
                return ("insufficient", e)

    # 用栅栏让两个事务尽量同时进入
    barrier = asyncio.Barrier(2)

    async def worker(txn_no: str):
        await barrier.wait()
        return await do_txn(txn_no)

    r1, r2 = await asyncio.gather(
        worker("TC03-SHIP-0001"), worker("TC03-SHIP-0002")
    )

    # 断言 1：恰好一成一败
    results = sorted([r1[0], r2[0]])
    assert results == ["insufficient", "ok"]

    # 断言 2：最终 on_hand == 2，不为负
    inv = (
        await session.execute(
            select(Inventory).where(
                Inventory.sku_id == sku_id,
                Inventory.location_id == location_id,
                Inventory.batch_no == batch,
            )
        )
    ).scalar_one()
    assert float(inv.qty_on_hand) == 2.0

    # 断言 3：流水只有 1 行
    cnt = (
        await session.execute(select(func.count()).select_from(StockTxn))
    ).scalar_one()
    assert cnt == 1

    # 断言 4：成功流快照自洽（before=10, after=2）
    ok_txn = r1[1] if r1[0] == "ok" else r2[1]
    assert float(ok_txn.before_on_hand) == 10.0
    assert float(ok_txn.after_on_hand) == 2.0


# ---------------------------------------------------------------------------
# TC-04 幂等
# ---------------------------------------------------------------------------
async def test_tc04_idempotent(session, base_ids):
    sku_id, location_id = base_ids["sku_id"], base_ids["location_id"]
    batch = "B20261004"

    # 前置：现有 100
    await _seed_inventory(session, sku_id, location_id, batch, on_hand=100, allocated=0)
    await session.commit()

    kwargs = dict(
        txn_no="TC04-PICK-0001",
        txn_type="PICK",
        sku_id=sku_id,
        location_id=location_id,
        batch_no=batch,
        on_hand_delta=-30,
        allocated_delta=0,
        source="PDA",
    )

    t1 = await apply_txn(session, **kwargs)
    await session.commit()

    # 第二次调用相同 txn_no
    t2 = await apply_txn(session, **kwargs)
    await session.commit()

    # 断言 1：两次返回同一条记录
    assert t1.id == t2.id

    # 断言 2：只扣了一次（100 - 30 = 70，不是 40）
    inv = (
        await session.execute(
            select(Inventory).where(
                Inventory.sku_id == sku_id,
                Inventory.location_id == location_id,
                Inventory.batch_no == batch,
            )
        )
    ).scalar_one()
    assert float(inv.qty_on_hand) == 70.0

    # 断言 3：该 txn_no 只有 1 行
    cnt = (
        await session.execute(
            select(func.count()).select_from(StockTxn).where(StockTxn.txn_no == "TC04-PICK-0001")
        )
    ).scalar_one()
    assert cnt == 1


# ---------------------------------------------------------------------------
# 工具：直接写 inventory 造前置数据（测试专用，绕过 apply_txn）
# ---------------------------------------------------------------------------
async def _seed_inventory(
    session, sku_id: int, location_id: int, batch: str, on_hand: float, allocated: float
):
    inv = Inventory(
        sku_id=sku_id,
        location_id=location_id,
        batch_no=batch,
        expiry_date=date.max,
        qty_on_hand=on_hand,
        qty_allocated=allocated,
        version=0,
    )
    session.add(inv)
    await session.flush()
