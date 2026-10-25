-- 自动生成：scripts/import-field-data.py
-- 来源：db/field-data/*.csv
-- 幂等：可重复执行

begin;

-- ============ SKU ============
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0001', '6901234567890', '矿泉水 550ml',
        '550ml*24/箱', '饮料', '箱',
        13.2, 365,
        true,
        50, 30,
        'A')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0002', '6901234567891', '可乐 330ml',
        '330ml*24/箱', '饮料', '箱',
        8.6, 270,
        true,
        40, 25,
        'A')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0003', '6901234567892', '纸巾 3层',
        '100抽*10包/提', '日用', '提',
        1.2, 1095,
        false,
        100, 60,
        'B')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0004', '6901234567893', '洗衣液 2kg',
        '2kg*6/箱', '日化', '箱',
        12.8, 730,
        true,
        30, 20,
        'B')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0005', '6901234567894', '方便面 红烧牛肉',
        '105g*24/箱', '食品', '箱',
        2.6, 180,
        true,
        80, 50,
        'A')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0006', '6901234567895', '牛奶 250ml',
        '250ml*16/箱', '乳品', '箱',
        4.3, 180,
        true,
        60, 35,
        'A')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0007', '6901234567896', '饼干 原味',
        '200g*20/箱', '食品', '箱',
        4.1, 240,
        true,
        40, 25,
        'C')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0008', '6901234567897', '洗发水 400ml',
        '400ml*12/箱', '日化', '箱',
        5.4, 1095,
        true,
        25, 15,
        'B')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0009', '6901234567898', '食用油 5L',
        '5L*4/箱', '粮油', '箱',
        19.2, 540,
        true,
        20, 12,
        'B')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                  weight_kg, shelf_life_days, is_batch_managed,
                  safety_stock, reorder_point, abc_class)
values ('SKU0010', '6901234567899', '大米 10kg',
        '10kg/袋', '粮油', '袋',
        10.0, 365,
        true,
        35, 20,
        'A')
on conflict (sku_code) do update set
  barcode = excluded.barcode, name = excluded.name, spec = excluded.spec,
  category = excluded.category, base_uom = excluded.base_uom,
  weight_kg = excluded.weight_kg, shelf_life_days = excluded.shelf_life_days,
  is_batch_managed = excluded.is_batch_managed,
  safety_stock = excluded.safety_stock, reorder_point = excluded.reorder_point,
  abc_class = excluded.abc_class;

-- ============ 库位 ============
-- location_code 直接取 bin_code（业务实际编码），不拼接
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'A',
        '01', 1,
        'A0101', 'A0101',
        'STORAGE',
        120,
        false,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'A',
        '01', 2,
        'A0102', 'A0102',
        'STORAGE',
        120,
        false,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'A',
        '02', 1,
        'A0201', 'A0201',
        'STORAGE',
        100,
        false,
        false)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'A',
        '02', 2,
        'A0202', 'A0202',
        'STORAGE',
        100,
        false,
        false)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'B',
        '01', 1,
        'B0101', 'B0101',
        'STORAGE',
        150,
        true,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'B',
        '01', 2,
        'B0102', 'B0102',
        'STORAGE',
        150,
        true,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'B',
        '02', 1,
        'B0201', 'B0201',
        'STORAGE',
        80,
        false,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'C',
        '01', 1,
        'C0101', 'C0101',
        'RECEIVING',
        200,
        true,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'C',
        '01', 2,
        'C0102', 'C0102',
        'RECEIVING',
        200,
        true,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'C',
        '02', 1,
        'C0201', 'C0201',
        'STAGING',
        200,
        true,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'C',
        '02', 2,
        'C0202', 'C0202',
        'STAGING',
        200,
        true,
        true)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'D',
        '01', 1,
        'D0101', 'D0101',
        'QUARANTINE',
        50,
        false,
        false)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;
insert into location (warehouse_code, zone_code, rack_code, level_no,
                  bin_code, location_code, location_type,
                  capacity_qty, is_mixed_sku, is_mixed_batch)
values ('WH01', 'D',
        '01', 2,
        'D0102', 'D0102',
        'QUARANTINE',
        50,
        false,
        false)
on conflict (location_code) do update set
  location_type = excluded.location_type,
  capacity_qty = excluded.capacity_qty,
  is_mixed_sku = excluded.is_mixed_sku,
  is_mixed_batch = excluded.is_mixed_batch;

-- ============ 库存余额 + 期初流水 ============
-- 每个维度两条：RECEIPT（现有量）+ ALLOCATE（已分配量）
-- SKU0001 @ A0101 批次 B20260101
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260101', date '2027-01-01',
       80, 20, 0
from sku s, location l where s.sku_code = 'SKU0001' and l.location_code = 'A0101'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0001-A0101-B20260101-R', 'RECEIPT', s.id, l.id, 'B20260101',
       date '2027-01-01', 80, 0, 0, 80,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0001' and l.location_code = 'A0101'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0001-A0101-B20260101-A', 'ALLOCATE', s.id, l.id, 'B20260101',
       date '2027-01-01', 0, 20, 80, 80,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0001' and l.location_code = 'A0101'
on conflict (txn_no) do nothing;

-- SKU0001 @ A0102 批次 B20260215
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260215', date '2027-02-15',
       60, 0, 0
from sku s, location l where s.sku_code = 'SKU0001' and l.location_code = 'A0102'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0001-A0102-B20260215-R', 'RECEIPT', s.id, l.id, 'B20260215',
       date '2027-02-15', 60, 0, 0, 60,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0001' and l.location_code = 'A0102'
on conflict (txn_no) do nothing;

-- SKU0002 @ B0101 批次 B20260110
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260110', date '2026-10-10',
       45, 10, 0
from sku s, location l where s.sku_code = 'SKU0002' and l.location_code = 'B0101'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0002-B0101-B20260110-R', 'RECEIPT', s.id, l.id, 'B20260110',
       date '2026-10-10', 45, 0, 0, 45,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0002' and l.location_code = 'B0101'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0002-B0101-B20260110-A', 'ALLOCATE', s.id, l.id, 'B20260110',
       date '2026-10-10', 0, 10, 45, 45,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0002' and l.location_code = 'B0101'
on conflict (txn_no) do nothing;

-- SKU0003 @ B0201 批次 (无)
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, '', date '9999-12-30',
       100, 15, 0
from sku s, location l where s.sku_code = 'SKU0003' and l.location_code = 'B0201'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0003-B0201-NOBATCH-R', 'RECEIPT', s.id, l.id, '',
       date '9999-12-30', 100, 0, 0, 100,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0003' and l.location_code = 'B0201'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0003-B0201-NOBATCH-A', 'ALLOCATE', s.id, l.id, '',
       date '9999-12-30', 0, 15, 100, 100,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0003' and l.location_code = 'B0201'
on conflict (txn_no) do nothing;

-- SKU0004 @ A0201 批次 B20260301
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260301', date '2028-03-01',
       30, 5, 0
from sku s, location l where s.sku_code = 'SKU0004' and l.location_code = 'A0201'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0004-A0201-B20260301-R', 'RECEIPT', s.id, l.id, 'B20260301',
       date '2028-03-01', 30, 0, 0, 30,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0004' and l.location_code = 'A0201'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0004-A0201-B20260301-A', 'ALLOCATE', s.id, l.id, 'B20260301',
       date '2028-03-01', 0, 5, 30, 30,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0004' and l.location_code = 'A0201'
on conflict (txn_no) do nothing;

-- SKU0005 @ B0102 批次 B20260120
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260120', date '2026-07-20',
       70, 30, 0
from sku s, location l where s.sku_code = 'SKU0005' and l.location_code = 'B0102'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0005-B0102-B20260120-R', 'RECEIPT', s.id, l.id, 'B20260120',
       date '2026-07-20', 70, 0, 0, 70,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0005' and l.location_code = 'B0102'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0005-B0102-B20260120-A', 'ALLOCATE', s.id, l.id, 'B20260120',
       date '2026-07-20', 0, 30, 70, 70,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0005' and l.location_code = 'B0102'
on conflict (txn_no) do nothing;

-- SKU0006 @ A0101 批次 B20260201
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260201', date '2026-08-01',
       55, 25, 0
from sku s, location l where s.sku_code = 'SKU0006' and l.location_code = 'A0101'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0006-A0101-B20260201-R', 'RECEIPT', s.id, l.id, 'B20260201',
       date '2026-08-01', 55, 0, 0, 55,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0006' and l.location_code = 'A0101'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0006-A0101-B20260201-A', 'ALLOCATE', s.id, l.id, 'B20260201',
       date '2026-08-01', 0, 25, 55, 55,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0006' and l.location_code = 'A0101'
on conflict (txn_no) do nothing;

-- SKU0006 @ A0202 批次 B20260210
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260210', date '2026-08-10',
       40, 0, 0
from sku s, location l where s.sku_code = 'SKU0006' and l.location_code = 'A0202'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0006-A0202-B20260210-R', 'RECEIPT', s.id, l.id, 'B20260210',
       date '2026-08-10', 40, 0, 0, 40,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0006' and l.location_code = 'A0202'
on conflict (txn_no) do nothing;

-- SKU0007 @ B0101 批次 B20260105
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260105', date '2026-09-05',
       35, 5, 0
from sku s, location l where s.sku_code = 'SKU0007' and l.location_code = 'B0101'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0007-B0101-B20260105-R', 'RECEIPT', s.id, l.id, 'B20260105',
       date '2026-09-05', 35, 0, 0, 35,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0007' and l.location_code = 'B0101'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0007-B0101-B20260105-A', 'ALLOCATE', s.id, l.id, 'B20260105',
       date '2026-09-05', 0, 5, 35, 35,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0007' and l.location_code = 'B0101'
on conflict (txn_no) do nothing;

-- SKU0008 @ A0201 批次 B20260115
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260115', date '2029-01-15',
       25, 0, 0
from sku s, location l where s.sku_code = 'SKU0008' and l.location_code = 'A0201'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0008-A0201-B20260115-R', 'RECEIPT', s.id, l.id, 'B20260115',
       date '2029-01-15', 25, 0, 0, 25,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0008' and l.location_code = 'A0201'
on conflict (txn_no) do nothing;

-- SKU0009 @ A0202 批次 B20260220
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260220', date '2027-08-20',
       18, 3, 0
from sku s, location l where s.sku_code = 'SKU0009' and l.location_code = 'A0202'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0009-A0202-B20260220-R', 'RECEIPT', s.id, l.id, 'B20260220',
       date '2027-08-20', 18, 0, 0, 18,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0009' and l.location_code = 'A0202'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0009-A0202-B20260220-A', 'ALLOCATE', s.id, l.id, 'B20260220',
       date '2027-08-20', 0, 3, 18, 18,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0009' and l.location_code = 'A0202'
on conflict (txn_no) do nothing;

-- SKU0010 @ B0201 批次 B20260101
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260101', date '2027-01-01',
       32, 12, 0
from sku s, location l where s.sku_code = 'SKU0010' and l.location_code = 'B0201'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0010-B0201-B20260101-R', 'RECEIPT', s.id, l.id, 'B20260101',
       date '2027-01-01', 32, 0, 0, 32,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0010' and l.location_code = 'B0201'
on conflict (txn_no) do nothing;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                      expiry_date, on_hand_delta, allocated_delta,
                      before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0010-B0201-B20260101-A', 'ALLOCATE', s.id, l.id, 'B20260101',
       date '2027-01-01', 0, 12, 32, 32,
       'IMPORT', 'IMPORT', '期初导入·已分配（无关联单据，需业务确认）'
from sku s, location l where s.sku_code = 'SKU0010' and l.location_code = 'B0201'
on conflict (txn_no) do nothing;

-- SKU0002 @ C0101 批次 B20260310
insert into inventory (sku_id, location_id, batch_no, expiry_date,
                  qty_on_hand, qty_allocated, version)
select s.id, l.id, 'B20260310', date '2026-12-10',
       10, 0, 0
from sku s, location l where s.sku_code = 'SKU0002' and l.location_code = 'C0101'
on conflict (sku_id, location_id, batch_no, expiry_date) do update set
  qty_on_hand = excluded.qty_on_hand,
  qty_allocated = excluded.qty_allocated;
insert into stock_txn (txn_no, txn_type, sku_id, location_id, batch_no,
                  expiry_date, on_hand_delta, allocated_delta,
                  before_on_hand, after_on_hand, ref_type, source, remark)
select 'IMPORT-SKU0002-C0101-B20260310-R', 'RECEIPT', s.id, l.id, 'B20260310',
       date '2026-12-10', 10, 0, 0, 10,
       'IMPORT', 'IMPORT', '期初导入·现有量'
from sku s, location l where s.sku_code = 'SKU0002' and l.location_code = 'C0101'
on conflict (txn_no) do nothing;

commit;

-- 导入后自检
select recon_status, count(*) from v_inventory_recon group by 1 order by 1;