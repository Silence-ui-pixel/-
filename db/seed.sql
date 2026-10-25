-- =============================================================================
-- 种子数据 · 仅开发 / 演示环境使用，生产环境不要执行
--
-- 使用方法：
--   psql -f db/schema.sql   建结构（只跑一次）
--   psql -f db/seed.sql     播种（可以反复跑）
--
-- 幂等设计：
--   每条 insert 都带 `on conflict ... do nothing`，重复执行不会报错、
--   也不会把期初库存重复累加。这条不是洁癖 —— 本地开发、CI 建库、
--   演示环境重建都会重复跑它，一次 duplicate key 就足以让新人卡住半小时。
--
-- 为什么和 schema.sql 分开：
--   DDL 是「只跑一次」的，种子是「随时重跑」的。混在一个文件里，
--   要么整个文件不可重跑（现在的问题），要么把 DDL 改成
--   `create table if not exists`，而那样会掩盖结构不一致 —— 更危险。
--   后续接入 alembic 时，迁移只覆盖 DDL，seed 由脚本单独调用。
-- =============================================================================

-- 用户
insert into app_user (username, display_name, password_hash, role) values
  ('admin',  '系统管理员', '$2b$12$REPLACE_WITH_REAL_BCRYPT_HASH', 'ADMIN'),
  ('sup01',  '张主管',     '$2b$12$REPLACE_WITH_REAL_BCRYPT_HASH', 'MANAGER'),
  ('op01',   '李操作员',   '$2b$12$REPLACE_WITH_REAL_BCRYPT_HASH', 'OPERATOR')
on conflict (username) do nothing;

-- 库位：A 区 2 货架 x 3 层 x 2 位，加 1 个拣货位 + 1 个收货暂存位
insert into location
  (zone_code, rack_code, level_no, bin_code, location_code, location_type, pick_seq, capacity_qty)
values
  ('A','01',1,'01','WH01-A-01-01-01','STORAGE', 1, 500),
  ('A','01',1,'02','WH01-A-01-01-02','STORAGE', 2, 500),
  ('A','01',2,'01','WH01-A-01-02-01','STORAGE', 3, 400),
  ('A','01',2,'02','WH01-A-01-02-02','STORAGE', 4, 400),
  ('A','02',1,'01','WH01-A-02-01-01','STORAGE', 5, 600),
  ('A','02',1,'02','WH01-A-02-01-02','STORAGE', 6, 600),
  ('A','00',1,'01','WH01-A-00-01-01','PICKING', 0, 100),
  ('R','00',1,'01','WH01-R-00-01-01','RECEIVING', null, 9999)
on conflict (location_code) do nothing;

-- 商品
insert into sku (sku_code, barcode, name, spec, category, base_uom,
                 shelf_life_days, abc_class, is_batch_managed, safety_stock, reorder_point)
values
  ('SKU-1001','6901234567890','矿泉水 550ml','550ml*24/箱','饮品','BOX', 365,'A', true,  50, 120),
  ('SKU-1002','6901234567891','抽纸 3 层','3层*6包/提','日用品','PACK', null,'B', false, 80, 200),
  ('SKU-1003','6901234567892','鲜牛奶 250ml','250ml*12/箱','冷链','BOX', 21,'A', true,  30,  80)
on conflict (sku_code) do nothing;

-- 期初库存：余额与流水必须成对写入，否则对账视图会立刻报 ONLY_INVENTORY
insert into inventory (sku_id, location_id, batch_no, expiry_date, qty_on_hand)
select s.id, l.id, 'B20261001', date '2027-10-01', 200
  from sku s, location l
 where s.sku_code = 'SKU-1001' and l.location_code = 'WH01-A-01-01-01'
on conflict (sku_id, location_id, batch_no, expiry_date) do nothing;

insert into stock_txn
  (txn_no, txn_type, sku_id, location_id, batch_no, expiry_date,
   on_hand_delta, allocated_delta, before_on_hand, after_on_hand,
   ref_type, source, operator_id, remark)
select 'TXN-INIT-0001', 'RECEIPT', s.id, l.id, 'B20261001', date '2027-10-01',
       200, 0, 0, 200, 'MANUAL', 'IMPORT',
       (select id from app_user where username = 'admin'), '期初导入'
  from sku s, location l
 where s.sku_code = 'SKU-1001' and l.location_code = 'WH01-A-01-01-01'
on conflict (txn_no) do nothing;

-- 自检：应当返回 1 行 OK
-- select recon_status, count(*) from v_inventory_recon group by 1;
