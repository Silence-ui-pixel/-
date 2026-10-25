"""P1 第 3 批接口测试：核心作业（收货 / 上架 / 分配 / 拣货 / 发运）。

这批是全系统唯一真正动库存的测试，重点验证三件事：
  1. 全链路走完，账实一致（对账视图无异常记录）
  2. 每一步的库存变化方向和位置都对（暂存位 vs 存储位）
  3. 异常场景不会留下脏数据（库存不足、状态非法、重复请求）

测试直接用 SQL 造库存（_seed_stock），同时写 inventory + stock_txn，
保证对账视图是 OK 的 —— 只插 inventory 不插流水，对账会报 ONLY_INVENTORY。
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.main import app

RECEIVING = "WH01-R-00-01-01"
STAGING = "WH01-S-00-01-01"
STORAGE = "WH01-A-01-01-01"
BATCH = "B-T3-01"


@pytest.fixture
async def client(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def clean_all(session):
    """清空库存与单据。CASCADE 会一并清掉 order_line。"""
    await session.execute(
        text(
            "TRUNCATE stock_txn, inventory, inbound_order, outbound_order "
            "RESTART IDENTITY CASCADE"
        )
    )
    await session.commit()
    yield


async def _login(client, username="admin", password="admin123"):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _ids(session):
    """取种子数据的 sku_id 与三个功能库位 id。"""
    sku_id = (
        await session.execute(text("select id from sku where sku_code = 'SKU-1001'"))
    ).scalar_one()
    rows = (
        await session.execute(
            text("select location_code, id from location where location_code = any(:cs)"),
            {"cs": [RECEIVING, STAGING, STORAGE]},
        )
    ).all()
    locs = {r.location_code: r.id for r in rows}
    assert len(locs) == 3, f"种子库位不全: {locs}"
    return sku_id, locs


async def _stock_at(session, sku_id: int, location_code: str) -> float:
    """某库位上某 SKU 的现有量合计。"""
    return float(
        (
            await session.execute(
                text(
                    "select coalesce(sum(i.qty_on_hand), 0) from inventory i "
                    "join location l on l.id = i.location_id "
                    "where i.sku_id = :s and l.location_code = :lc"
                ),
                {"s": sku_id, "lc": location_code},
            )
        ).scalar_one()
    )


async def _allocated_at(session, sku_id: int, location_code: str) -> float:
    return float(
        (
            await session.execute(
                text(
                    "select coalesce(sum(i.qty_allocated), 0) from inventory i "
                    "join location l on l.id = i.location_id "
                    "where i.sku_id = :s and l.location_code = :lc"
                ),
                {"s": sku_id, "lc": location_code},
            )
        ).scalar_one()
    )


async def _recon_bad(session) -> int:
    return (
        await session.execute(
            text("select count(*) from v_inventory_recon where recon_status <> 'OK'")
        )
    ).scalar_one()


async def _seed_stock(session, sku_id, location_id, batch, expiry, qty):
    """测试专用造库存：余额 + 流水成对写入，保证对账 OK。

    expiry 必须是 date 对象 —— asyncpg 不接受字符串直接绑到 date 列
    （会报 'str' object has no attribute 'toordinal'）。
    """
    if isinstance(expiry, str):
        expiry = date.fromisoformat(expiry)
    await session.execute(
        text(
            "insert into inventory (sku_id, location_id, batch_no, expiry_date, "
            "qty_on_hand, qty_allocated) values (:s, :l, :b, :e, :q, 0) "
            "on conflict (sku_id, location_id, batch_no, expiry_date) "
            "do update set qty_on_hand = excluded.qty_on_hand"
        ),
        {"s": sku_id, "l": location_id, "b": batch, "e": expiry, "q": qty},
    )
    await session.execute(
        text(
            "insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no, "
            "expiry_date, on_hand_delta, allocated_delta, before_on_hand, "
            "after_on_hand, source) "
            "values (:no, 'RECEIPT', :s, :l, :b, :e, :q, 0, 0, :q, 'IMPORT')"
        ),
        {
            "no": f"SEED-{batch}-{location_id}",
            "s": sku_id,
            "l": location_id,
            "b": batch,
            "e": expiry,
            "q": qty,
        },
    )
    await session.commit()


# ---------------------------------------------------------------------------
# 全链路：入库
# ---------------------------------------------------------------------------
async def test_inbound_full_flow(client, session, clean_all):
    """建单 → 收货 → 上架，货最终落到存储位，暂存位归零，账实一致。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)

    # 1. 建单
    created = await client.post(
        "/api/v1/inbound-orders",
        json={
            "order_type": "PO",
            "supplier_name": "全链路供应商",
            "lines": [{"sku_id": sku_id, "qty_required": 100}],
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    order = created.json()
    order_id, line_id = order["id"], order["lines"][0]["id"]

    # 2. 收货
    received = await client.post(
        f"/api/v1/inbound-orders/{order_id}/receive",
        json={
            "lines": [
                {
                    "line_id": line_id,
                    "qty_actual": 100,
                    "qty_rejected": 0,
                    "batch_no": BATCH,
                    "expiry_date": "2027-01-01",
                }
            ]
        },
        headers={**_auth(token), "Idempotency-Key": "rcv-1"},
    )
    assert received.status_code == 200, received.text
    assert received.json()["status"] == "RECEIVED"
    assert received.json()["total_received_qty"] == 100

    # 收货后：货在收货暂存位，存储位还是空的
    assert await _stock_at(session, sku_id, RECEIVING) == 100
    assert await _stock_at(session, sku_id, STORAGE) == 0

    # 3. 上架
    putaway = await client.post(
        f"/api/v1/inbound-orders/{order_id}/putaway",
        json={"lines": [{"line_id": line_id}]},
        headers={**_auth(token), "Idempotency-Key": "put-1"},
    )
    assert putaway.status_code == 200, putaway.text
    assert putaway.json()["status"] == "DONE"
    assert putaway.json()["lines"][0]["to_location_id"] is not None

    # 上架后：货移到存储位，暂存位归零
    assert await _stock_at(session, sku_id, RECEIVING) == 0
    assert await _stock_at(session, sku_id, STORAGE) == 100

    # 账实一致
    assert await _recon_bad(session) == 0


async def test_receive_requires_batch_for_batch_managed(client, session, clean_all):
    """批次管理商品不传批次号必须拒绝 —— 否则批次追溯直接断链。"""
    token = await _login(client)
    sku_id, _ = await _ids(session)

    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_id, "qty_required": 10}]},
        headers=_auth(token),
    )
    order = created.json()

    resp = await client.post(
        f"/api/v1/inbound-orders/{order['id']}/receive",
        json={"lines": [{"line_id": order["lines"][0]["id"], "qty_actual": 10}]},
        headers=_auth(token),
    )
    assert resp.status_code == 422
    assert "批次" in resp.json()["detail"]


async def test_receive_twice_returns_conflict(client, session, clean_all):
    """重复收货必须 409，且库存不能翻倍。"""
    token = await _login(client)
    sku_id, _ = await _ids(session)

    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_id, "qty_required": 20}]},
        headers=_auth(token),
    )
    order = created.json()
    body = {
        "lines": [
            {
                "line_id": order["lines"][0]["id"],
                "qty_actual": 20,
                "batch_no": BATCH,
                "expiry_date": "2027-01-01",
            }
        ]
    }

    first = await client.post(
        f"/api/v1/inbound-orders/{order['id']}/receive",
        json=body,
        headers=_auth(token),
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/inbound-orders/{order['id']}/receive",
        json=body,
        headers=_auth(token),
    )
    assert second.status_code == 409
    err = second.json()
    assert err["code"] == "INVALID_STATUS_TRANSITION"
    assert err["detail"]["current_status"] == "RECEIVED"

    # 关键：库存没被重复加
    assert await _stock_at(session, sku_id, RECEIVING) == 20


# ---------------------------------------------------------------------------
# 全链路：出库
# ---------------------------------------------------------------------------
async def test_outbound_full_flow(client, session, clean_all):
    """建单 → 分配 → 拣货 → 发运，每步库存位置都对，最后账实一致。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)
    await _seed_stock(session, sku_id, locs[STORAGE], BATCH, "2027-01-01", 200)

    # 1. 建单 30 件
    created = await client.post(
        "/api/v1/outbound-orders",
        json={
            "order_type": "SALE",
            "customer_name": "全链路客户",
            "lines": [{"sku_id": sku_id, "qty_required": 30}],
        },
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    order = created.json()
    order_id, line_id = order["id"], order["lines"][0]["id"]

    # 2. 分配：只锁 allocated，on_hand 不变
    allocated = await client.post(
        f"/api/v1/outbound-orders/{order_id}/allocate",
        headers={**_auth(token), "Idempotency-Key": "alc-1"},
    )
    assert allocated.status_code == 200, allocated.text
    assert allocated.json()["status"] == "ALLOCATED"
    assert allocated.json()["lines"][0]["from_location_id"] == locs[STORAGE]
    assert await _stock_at(session, sku_id, STORAGE) == 200
    assert await _allocated_at(session, sku_id, STORAGE) == 30

    # 3. 拣货路径
    plan = await client.get(
        f"/api/v1/outbound-orders/{order_id}/pick", headers=_auth(token)
    )
    assert plan.status_code == 200
    assert plan.json()["lines"][0]["location_code"] == STORAGE
    assert plan.json()["lines"][0]["qty_required"] == 30

    # 4. 拣货：存储位 -30，发货暂存位 +30
    picked = await client.post(
        f"/api/v1/outbound-orders/{order_id}/pick",
        json={"lines": [{"line_id": line_id, "qty_actual": 30}]},
        headers={**_auth(token), "Idempotency-Key": "pck-1"},
    )
    assert picked.status_code == 200, picked.text
    assert picked.json()["status"] == "PICKED"
    assert await _stock_at(session, sku_id, STORAGE) == 170
    assert await _stock_at(session, sku_id, STAGING) == 30
    assert await _allocated_at(session, sku_id, STORAGE) == 0

    # 5. 发运：发货暂存位归零
    shipped = await client.post(
        f"/api/v1/outbound-orders/{order_id}/ship",
        json={"carrier": "顺丰", "tracking_no": "SF123456"},
        headers={**_auth(token), "Idempotency-Key": "shp-1"},
    )
    assert shipped.status_code == 200, shipped.text
    data = shipped.json()
    assert data["status"] == "SHIPPED"
    assert data["carrier"] == "顺丰"
    assert data["tracking_no"] == "SF123456"
    assert data["shipped_at"] is not None
    assert await _stock_at(session, sku_id, STAGING) == 0
    assert await _stock_at(session, sku_id, STORAGE) == 170

    assert await _recon_bad(session) == 0


async def test_allocate_insufficient_returns_409_with_detail(client, session, clean_all):
    """库存不足必须 409 且 detail 带三数，前端才能显示「差多少」。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)
    # 只有 5 件，却要 100
    await _seed_stock(session, sku_id, locs[STORAGE], BATCH, "2027-01-01", 5)

    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_id, "qty_required": 100}]},
        headers=_auth(token),
    )
    order = created.json()

    resp = await client.post(
        f"/api/v1/outbound-orders/{order['id']}/allocate", headers=_auth(token)
    )
    assert resp.status_code == 409
    err = resp.json()
    assert err["code"] == "INVENTORY_INSUFFICIENT"
    d = err["detail"]
    assert d["required"] == 100
    assert d["available"] == 5
    assert d["shortfall"] == 95
    assert "SKU-1001" == d["sku_code"]

    # 关键：失败不能留下半分配状态
    assert await _allocated_at(session, sku_id, STORAGE) == 0
    detail = await client.get(
        f"/api/v1/outbound-orders/{order['id']}", headers=_auth(token)
    )
    assert detail.json()["status"] == "DRAFT"


async def test_pick_without_allocate_conflict(client, session, clean_all):
    """未分配就拣货必须 409（状态机挡住）。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)
    await _seed_stock(session, sku_id, locs[STORAGE], BATCH, "2027-01-01", 50)

    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_id, "qty_required": 10}]},
        headers=_auth(token),
    )
    order = created.json()

    resp = await client.post(
        f"/api/v1/outbound-orders/{order['id']}/pick",
        json={"lines": [{"line_id": order["lines"][0]["id"], "qty_actual": 10}]},
        headers=_auth(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_STATUS_TRANSITION"


async def test_cancel_allocated_releases_stock(client, session, clean_all):
    """取消已分配的单必须把锁定的库存放回去，否则是永久性库存泄漏。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)
    await _seed_stock(session, sku_id, locs[STORAGE], BATCH, "2027-01-01", 50)

    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_id, "qty_required": 20}]},
        headers=_auth(token),
    )
    order = created.json()

    await client.post(
        f"/api/v1/outbound-orders/{order['id']}/allocate", headers=_auth(token)
    )
    assert await _allocated_at(session, sku_id, STORAGE) == 20

    cancelled = await client.post(
        f"/api/v1/outbound-orders/{order['id']}/cancel", headers=_auth(token)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    # 锁定必须归零，可用量恢复
    assert await _allocated_at(session, sku_id, STORAGE) == 0
    assert await _stock_at(session, sku_id, STORAGE) == 50
    assert await _recon_bad(session) == 0


async def test_allocate_prefers_earliest_expiry(client, session, clean_all):
    """FEFO：两个批次都有货时，必须优先出效期早的那个。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)

    # 同库位两个批次：晚效期先造，早效期后造（排除「按插入顺序」的假象）
    await _seed_stock(session, sku_id, locs[STORAGE], "B-LATE", "2027-06-01", 100)
    await _seed_stock(session, sku_id, locs[STORAGE], "B-EARLY", "2026-12-01", 100)

    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_id, "qty_required": 10}]},
        headers=_auth(token),
    )
    order = created.json()

    allocated = await client.post(
        f"/api/v1/outbound-orders/{order['id']}/allocate", headers=_auth(token)
    )
    assert allocated.status_code == 200, allocated.text
    assert allocated.json()["lines"][0]["batch_no"] == "B-EARLY"


async def test_short_pick_releases_full_allocation(client, session, clean_all):
    """短拣：实拣少于应拣时，锁定量必须全额解开，否则剩余库存永久卡住。"""
    token = await _login(client)
    sku_id, locs = await _ids(session)
    await _seed_stock(session, sku_id, locs[STORAGE], BATCH, "2027-01-01", 100)

    created = await client.post(
        "/api/v1/outbound-orders",
        json={"order_type": "SALE", "lines": [{"sku_id": sku_id, "qty_required": 40}]},
        headers=_auth(token),
    )
    order = created.json()

    await client.post(
        f"/api/v1/outbound-orders/{order['id']}/allocate", headers=_auth(token)
    )
    picked = await client.post(
        f"/api/v1/outbound-orders/{order['id']}/pick",
        json={"lines": [{"line_id": order["lines"][0]["id"], "qty_actual": 25}]},
        headers=_auth(token),
    )
    assert picked.status_code == 200, picked.text
    assert picked.json()["lines"][0]["status"] == "PARTIAL"

    # 锁定全额解开（不是只解 25）
    assert await _allocated_at(session, sku_id, STORAGE) == 0
    # 只实际拿走 25
    assert await _stock_at(session, sku_id, STORAGE) == 75
    assert await _stock_at(session, sku_id, STAGING) == 25
    assert await _recon_bad(session) == 0


async def test_agent_header_recorded_in_txn(client, session, clean_all):
    """带 X-Agent-Run-Id 的写操作，流水 source 必须是 AGENT（审计可追溯）。"""
    token = await _login(client)
    sku_id, _ = await _ids(session)

    created = await client.post(
        "/api/v1/inbound-orders",
        json={"order_type": "PO", "lines": [{"sku_id": sku_id, "qty_required": 15}]},
        headers=_auth(token),
    )
    order = created.json()

    await client.post(
        f"/api/v1/inbound-orders/{order['id']}/receive",
        json={
            "lines": [
                {
                    "line_id": order["lines"][0]["id"],
                    "qty_actual": 15,
                    "batch_no": BATCH,
                    "expiry_date": "2027-01-01",
                }
            ]
        },
        headers={**_auth(token), "X-Agent-Run-Id": "run-abc-123"},
    )

    row = (
        await session.execute(
            text(
                "select source, agent_run_id from stock_txn "
                "where txn_no = :no"
            ),
            {"no": f"RECEIPT-{order['id']}-{order['lines'][0]['id']}"},
        )
    ).first()
    assert row is not None
    assert row.source == "AGENT"
    assert row.agent_run_id == "run-abc-123"
