#!/usr/bin/env python
"""现场采集数据的校验脚本（P0 数据质量闸门）。

用途：把业务方回填的 CSV 在导入系统前先过一遍规则，把"数据本身的错误"
和"数据暴露出的业务问题"分开列出来。

两类问题要区分开：

  错误（ERROR）—— 数据自相矛盾，导入必然失败或产生脏数据，必须让业务方改
  警告（WARN） —— 数据合法但业务上有疑点，要跟业务方确认，不影响导入

用法：
    python scripts/validate-field-data.py [数据目录]
    # 默认读 db/field-data/
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

# 校验基准日：现场盘点日。用固定值而不是 today()，
# 否则同一份数据隔几天跑结论就变了，无法复盘。
AS_OF = date(2026, 10, 25)

VALID_LOCATION_TYPES = {"STORAGE", "RECEIVING", "PICKING", "STAGING", "QUARANTINE"}
VALID_ROLES = {"ADMIN", "MANAGER", "OPERATOR", "VIEWER"}

errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def load(root: Path, name: str) -> list[dict]:
    path = root / name
    if not path.exists():
        err(f"{name} 文件不存在")
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def main(root: Path) -> int:
    skus = load(root, "sku.csv")
    locs = load(root, "location.csv")
    invs = load(root, "inventory_snapshot.csv")
    users = load(root, "users.csv")

    # ------------------------------------------------------------------
    # 1. SKU
    # ------------------------------------------------------------------
    sku_map = {}
    for r in skus:
        code = r["sku_code"].strip()
        if code in sku_map:
            err(f"[SKU] 编码重复：{code}")
        sku_map[code] = r

        if not r["name"].strip():
            err(f"[SKU] {code} 缺商品名称")

        bc = r["barcode"].strip()
        if bc and (not bc.isdigit() or len(bc) != 13):
            warn(f"[SKU] {code} 条码不是 13 位数字：{bc}")
        if not bc:
            warn(f"[SKU] {code} 无条码，PDA 扫码无法录入该商品")

        # 批次管理商品必须有保质期，否则效期管理断链
        if r["is_batch_managed"] == "1" and not r["shelf_life_days"].strip():
            err(f"[SKU] {code} 是批次管理商品但缺 shelf_life_days")

        # 补货点 vs 安全库存的语义
        try:
            safety = float(r["safety_stock"] or 0)
            reorder = float(r["reorder_point"] or 0)
            if reorder < safety:
                warn(
                    f"[SKU] {code} 补货点({reorder}) < 安全库存({safety})，"
                    f"常规语义应相反，需确认业务定义"
                )
        except ValueError:
            err(f"[SKU] {code} safety_stock/reorder_point 不是数字")

        # 基础单位能否拆零：spec 里出现了 "*N/单位" 说明有一层包装换算
        uom = r["base_uom"].strip()
        if "*" in r["spec"] and uom not in ("EA", "个", "瓶", "包"):
            warn(
                f"[SKU] {code} 基础单位是「{uom}」但规格含包装换算（{r['spec']}），"
                f"系统不支持多单位换算，拆零销售无法表达"
            )

    # 条码唯一性
    seen_bc = defaultdict(list)
    for code, r in sku_map.items():
        bc = r["barcode"].strip()
        if bc:
            seen_bc[bc].append(code)
    for bc, codes in seen_bc.items():
        if len(codes) > 1:
            err(f"[SKU] 条码 {bc} 被多个 SKU 使用：{codes}（一码多品）")

    # ------------------------------------------------------------------
    # 2. 库位
    # ------------------------------------------------------------------
    loc_map = {}
    for r in locs:
        bin_code = r["bin_code"].strip()
        if bin_code in loc_map:
            err(f"[LOC] bin_code 重复：{bin_code}")
        loc_map[bin_code] = r

        lt = r["location_type"].strip()
        if lt not in VALID_LOCATION_TYPES:
            err(f"[LOC] {bin_code} location_type 非法：{lt}")

        # bin_code 是否已经把 zone/rack/level 编进去了
        expect_prefix = f"{r['zone_code']}{r['rack_code']}"
        if bin_code.startswith(expect_prefix) and len(bin_code) > len(expect_prefix):
            warn(
                f"[LOC] {bin_code} 的 bin_code 已包含区+架（{expect_prefix}），"
                f"与 zone_code/rack_code 字段重复，location_code 需确认拼接规则"
            )

    present_types = {r["location_type"].strip() for r in locs}
    if "PICKING" not in present_types:
        warn("[LOC] 没有 PICKING（拣货位）库位，拣货将直接从 STORAGE 出——需确认是否符合实际")
    if "RECEIVING" not in present_types:
        err("[LOC] 没有 RECEIVING（收货暂存位），收货接口无处落货，无法工作")
    if "STAGING" not in present_types:
        err("[LOC] 没有 STAGING（发货暂存位），拣货后无处放，无法工作")

    # ------------------------------------------------------------------
    # 3. 库存快照
    # ------------------------------------------------------------------
    # 每个库位上的 SKU 集合（用于混放检查）
    loc_skus: dict[str, set[str]] = defaultdict(set)
    loc_qty: dict[str, float] = defaultdict(float)

    for i, r in enumerate(invs, start=2):  # 从 2 开始：1 是表头
        code = r["sku_code"].strip()
        loc = r["location_code"].strip()

        sku = sku_map.get(code)
        if sku is None:
            err(f"[INV] 第{i}行 商品不存在：{code}")
            continue
        locrow = loc_map.get(loc)
        if locrow is None:
            err(f"[INV] 第{i}行 库位不存在：{loc}")
            continue

        try:
            on_hand = float(r["qty_on_hand"] or 0)
            allocated = float(r["qty_allocated"] or 0)
        except ValueError:
            err(f"[INV] 第{i}行 数量不是数字")
            continue

        if allocated > on_hand:
            err(f"[INV] {code}@{loc} 已分配({allocated}) > 现有({on_hand})，违反 ck_inv_allocated")

        # 批次管理一致性
        batch = r["batch_no"].strip()
        expiry = parse_date(r["expiry_date"])
        if sku["is_batch_managed"] == "1" and not batch:
            err(f"[INV] {code}@{loc} 是批次管理商品但无 batch_no，收货/追溯会断链")
        if sku["is_batch_managed"] == "0" and batch:
            warn(f"[INV] {code}@{loc} 非批次管理商品却填了批次 {batch}，导入时会被忽略")

        # 效期
        if sku["is_batch_managed"] == "1":
            if expiry is None:
                err(f"[INV] {code}@{loc} 批次管理商品缺 expiry_date")
            elif expiry < AS_OF:
                days = (AS_OF - expiry).days
                warn(
                    f"[INV] {code}@{loc} 批次 {batch} 已过期 {days} 天"
                    f"（效期 {expiry}，现有 {on_hand}，已分配 {allocated}）"
                    + ("　← 过期货已分配，FEFO 会优先把它发出去！" if allocated > 0 else "")
                )

        # 库位类型合理性
        lt = locrow["location_type"].strip()
        if lt in ("RECEIVING", "STAGING"):
            warn(
                f"[INV] {code}@{loc} 库位类型是 {lt}（临时区）却存有 {on_hand}，"
                f"长期存放不合理；且 FEFO 只从 STORAGE 选批次，这批货会被永久跳过"
            )
        if lt == "QUARANTINE":
            warn(f"[INV] {code}@{loc} 在隔离区有 {on_hand}，属正常（待检/不良品），确认是否要计入可用")

        loc_skus[loc].add(code)
        loc_qty[loc] += on_hand

    # 混放检查
    for loc, codes in loc_skus.items():
        if len(codes) > 1 and loc_map[loc]["is_mixed_sku"] == "0":
            err(
                f"[INV] {loc} 标记 is_mixed_sku=0（不允许混放），"
                f"实际放了 {len(codes)} 个 SKU：{sorted(codes)}"
            )

    # 容量检查
    for loc, total in loc_qty.items():
        cap_raw = loc_map[loc]["capacity_qty"].strip()
        if not cap_raw:
            continue
        try:
            cap = float(cap_raw)
        except ValueError:
            continue
        if cap > 0 and total > cap:
            err(f"[INV] {loc} 总库存 {total} 超过容量 {cap}（超 {total - cap}）")

    # 同库位同批次的重复行（会被唯一键撞）
    dims = defaultdict(list)
    for r in invs:
        key = (
            r["sku_code"].strip(),
            r["location_code"].strip(),
            r["batch_no"].strip(),
            r["expiry_date"].strip() or "9999-12-30",
        )
        dims[key].append(r)
    for key, rows in dims.items():
        if len(rows) > 1:
            err(f"[INV] 唯一维度重复 {key}，出现 {len(rows)} 行，导入会撞 uk_inventory_dim")

    # ------------------------------------------------------------------
    # 4. 用户
    # ------------------------------------------------------------------
    seen_user = set()
    for r in users:
        u = r["username"].strip()
        if u in seen_user:
            err(f"[USER] username 重复：{u}")
        seen_user.add(u)
        if r["role"].strip() not in VALID_ROLES:
            err(f"[USER] {u} 角色非法：{r['role']}")

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    print(f"校验基准日：{AS_OF}")
    print(f"数据量：SKU {len(skus)} / 库位 {len(locs)} / 库存行 {len(invs)} / 用户 {len(users)}")
    print()

    if errors:
        print(f"❌ 错误 {len(errors)} 条（数据自相矛盾，导入前必须修）")
        for e in errors:
            print(f"   - {e}")
        print()
    else:
        print("✅ 无错误")
        print()

    if warns:
        print(f"⚠️  警告 {len(warns)} 条（数据合法但有业务疑点，需与业务方确认）")
        for w in warns:
            print(f"   - {w}")
        print()

    # 统计概览
    print("── 库存分布 ──")
    by_loc_type = defaultdict(float)
    for r in invs:
        loc = r["location_code"].strip()
        if loc in loc_map:
            by_loc_type[loc_map[loc]["location_type"].strip()] += float(r["qty_on_hand"] or 0)
    for t, q in sorted(by_loc_type.items()):
        print(f"   {t:12s} {q:8.0f}")

    total = sum(float(r["qty_on_hand"] or 0) for r in invs)
    alloc = sum(float(r["qty_allocated"] or 0) for r in invs)
    print(f"   {'合计':12s} {total:8.0f}（已分配 {alloc:.0f}，可用 {total - alloc:.0f}）")

    return 1 if errors else 0


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("db/field-data")
    if not root.is_absolute():
        root = Path.cwd() / root
    sys.exit(main(root))
