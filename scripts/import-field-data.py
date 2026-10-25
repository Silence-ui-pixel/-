#!/usr/bin/env python
"""现场采集数据导入器：CSV -> SQL。

设计要点（为什么不是一个一个手写 INSERT）：

1. **必须成对写 inventory + stock_txn**
   对账视图 v_inventory_recon 同时校验 on_hand 和 allocated，
   只写余额不写流水会立刻报 ONLY_INVENTORY，等于给自己造脏数据。

2. **allocated 单独用一条 ALLOCATE 流水**
   快照里的 qty_allocated 是"已锁定未发运"，不是收货带来的。
   所以每个维度写两条流水：RECEIPT（加现有）+ ALLOCATE（加分配量）。

3. **幂等**
   全部用固定 txn_no（IMPORT-{sku}-{loc}-{batch}-R / -A）+ ON CONFLICT DO NOTHING，
   重复跑不会翻倍，也不受 stock_txn 只追加触发器影响。

4. **非批次商品的哨兵值**
   is_batch_managed=0 的商品：batch_no='' 、expiry_date 用 9999-12-30
   （不能用 date.max，asyncpg 会编码成 infinity 导致唯一约束维度错配）。

用法：
    python scripts/import-field-data.py [数据目录]
    # 生成 import.sql，然后：
    docker compose exec -T db psql -v ON_ERROR_STOP=1 -U canku -d canku < db/field-data/import.sql
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

SENTINEL_EXPIRY = "9999-12-30"


def sql_str(v: str) -> str:
    """转义为 SQL 字符串字面量。"""
    return "'" + (v or "").replace("'", "''") + "'"


def sql_num(v: str) -> str:
    v = (v or "").strip()
    return v if v else "0"


def main(root: Path) -> int:
    sku_rows = list(csv.DictReader((root / "sku.csv").open(encoding="utf-8-sig")))
    loc_rows = list(csv.DictReader((root / "location.csv").open(encoding="utf-8-sig")))
    inv_rows = list(csv.DictReader((root / "inventory_snapshot.csv").open(encoding="utf-8-sig")))

    out: list[str] = []
    out.append("-- 自动生成：scripts/import-field-data.py")
    out.append("-- 来源：db/field-data/*.csv")
    out.append("-- 幂等：可重复执行")
    out.append("")
    out.append("begin;")
    out.append("")

    # ---------------- SKU ----------------
    out.append("-- ============ SKU ============")
    for r in sku_rows:
        out.append(
            f"""insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ({sql_str(r['sku_code'])}, {sql_str(r['barcode'])}, {sql_str(r['name'])},
        {sql_str(r['spec'])}, {sql_str(r['category'])}, {sql_str(r['base_uom'])},
        {sql_num(r['weight_kg'])}, {sql_num(r['shelf_life_days']) or 'null'},
        {'true' if r['is_batch_managed'].strip() == '1' else 'false'},
        {sql_num(r['safety_stock'])}, {sql_num(r['reorder_point'])},
        {sql_str(r['abc_class'])})
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;"""
        )
    out.append("")

    # ---------------- 库位 ----------------
    # location_code 直接用 bin_code：业务方实际就用这个编码（A0101），
    # 拼接 warehouse-zone-rack-level-bin 会得到 WH01-A-01-1-A0101 这种没人认得的串。
    out.append("-- ============ 库位 ============")
    out.append("-- location_code 直接取 bin_code（业务实际编码），不拼接")
    for r in loc_rows:
        out.append(
            f"""insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ({sql_str(r['warehouse_code'])}, {sql_str(r['zone_code'])},
        {sql_str(r['rack_code'])}, {r['level_no']},
        {sql_str(r['bin_code'])}, {sql_str(r['bin_code'])},
        {sql_str(r['location_type'])},
        {sql_num(r['capacity_qty']) or 'null'},
        {'true' if r['is_mixed_sku'].strip() == '1' else 'false'},
        {'true' if r['is_mixed_batch'].strip() == '1' else 'false'})
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;"""
        )
    out.append("")

    # ---------------- 库存 + 流水 ----------------
    out.append("-- ============ 库存余额 + 期初流水 ============")
    out.append("-- 每个维度两条：RECEIPT（现有量）+ ALLOCATE（已分配量）")
    for r in inv_rows:
        code = r["sku_code"].strip()
        loc = r["location_code"].strip()
        batch = r["batch_no"].strip()
        expiry = r["expiry_date"].strip() or SENTINEL_EXPIRY
        on_hand = sql_num(r["qty_on_hand"])
        alloc = sql_num(r["qty_allocated"])

        where = (
            f"from sku s, location l "
            f"where s.sku_code = {sql_str(code)} and l.location_code = {sql_str(loc)}"
        )
        txn_suffix = f"{code}-{loc}-{batch or 'NOBATCH'}".replace(" ", "")

        out.append(f"-- {code} @ {loc} 批次 {batch or '(无)'}")
        out.append(
            f"""insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, {sql_str(batch)}, date {sql_str(expiry)},
       {on_hand}, {alloc}, 0
{where}
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;"""
        )
        # 期初收货流水
        out.append(
            f"""insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-{txn_suffix}-R', 'RECEIPT', s.id, l.id, {sql_str(batch)},
       date {sql_str(expiry)}, {on_hand}, 0, 0, {on_hand},
       'IMPORT', 'IMPORT', '期初导入·现有量'
{where}
on conflict (txn_no) do nothing;"""
        )
        # 期初已分配（仅当 >0）
        if alloc not in ("0", "0.0"):
            out.append(
                f"""insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-{txn_suffix}-A', 'ALLOCATE', s.id, l.id, {sql_str(batch)},
       date {sql_str(expiry)}, 0, {alloc}, {on_hand}, {on_hand},
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
{where}
on conflict (txn_no) do nothing;"""
            )
        out.append("")

    out.append("commit;")
    out.append("")
    out.append("-- 导入后自检")
    out.append("select recon_status, count(*) from v_inventory_recon group by 1 order by 1;")

    target = root / "import.sql"
    target.write_text("\n".join(out), encoding="utf-8")

    print(f"✅ 已生成 {target}")
    print(f"   SKU {len(sku_rows)} 条 / 库位 {len(loc_rows)} 条 / 库存 {len(inv_rows)} 维")
    print()
    print("执行：")
    print(f"   docker compose exec -T db psql -v ON_ERROR_STOP=1 -U canku -d canku < {target.as_posix()}")
    return 0


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("db/field-data")
    if not root.is_absolute():
        root = Path.cwd() / root
    sys.exit(main(root))
