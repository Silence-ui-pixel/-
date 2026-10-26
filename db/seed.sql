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

-- 用户（开发环境密码：admin/admin123，sup01/sup123，op01/op123）
insert into app_user (username, display_name, password_hash, role) values
  ('admin',  '系统管理员', '$2b$12$AktH6N4KqTrK064UGxFzGuBD/Q82z9Fnr5ERz/0M8mBAnYXCo2s.O', 'ADMIN'),
  ('sup01',  '张主管',     '$2b$12$D.FLruIyjiUfJri9yt9XkOi1NpNkF31OBLcRAZMdcdjyHWlKn5wgq', 'MANAGER'),
  ('op01',   '李操作员',   '$2b$12$5Z8W3kiy/PQgZnhPrfdgaO7v/ZnC4CMbnZqzi.CsucObNoxyVubNC', 'OPERATOR')
on conflict (username) do nothing;

-- 库位：直接采用业务方现场给出的 13 个库位（db/field-data/location.csv）
--
-- 编码约定：location_code 取 bin_code（A0101），不拼 warehouse-zone-rack-level-bin。
-- bin_code 本身已经含了 zone(A) + rack(01) + level(01)，再拼会得到
-- WH01-A-01-01-A0101 这种现场没人认得的串。
--
-- 历史坑：早期种子用的是拼接编码 WH01-A-01-01-01，和现场导入的 A0101
-- 是同一个物理位却存成两行。后果有两个，都很隐蔽：
--   1. 库位管理页显示 22 条，其中 6 对是同一个物理位
--   2. get_functional_location 按 id 取第一个 RECEIVING 位，永远命中
--      种子那个虚拟位，而现场真实暂存货在 C0101 —— 两处货互不相干
-- 所以现在种子与现场数据共用同一套编码，import.sql 会按 location_code upsert。
--
-- 功能位分工（对应作业流三段「暂存」）：
--   RECEIVING  收货暂存 —— 货到了但没上架，账上算它的，但不算「可拣」
--   STAGING    发货暂存 —— 已拣出但没发运，仍在账上（账实一致的最后一环）
--   QUARANTINE 隔离待检 —— 现场有 2 个位，当前空置，保留备用
insert into location
  (zone_code, rack_code, level_no, bin_code, location_code, location_type,
   pick_seq, capacity_qty, is_mixed_sku, is_mixed_batch)
values
  ('A','01',1,'A0101','A0101','STORAGE',    1, 120, false, true),
  ('A','01',2,'A0102','A0102','STORAGE',    2, 120, false, true),
  ('A','02',1,'A0201','A0201','STORAGE',    3, 100, false, false),
  ('A','02',2,'A0202','A0202','STORAGE',    4, 100, false, false),
  ('B','01',1,'B0101','B0101','STORAGE',    5, 150, true,  true),
  ('B','01',2,'B0102','B0102','STORAGE',    6, 150, true,  true),
  ('B','02',1,'B0201','B0201','STORAGE',    7,  80, false, true),
  ('C','01',1,'C0101','C0101','RECEIVING', null, 200, true,  true),
  ('C','01',2,'C0102','C0102','RECEIVING', null, 200, true,  true),
  ('C','02',1,'C0201','C0201','STAGING',   null, 200, true,  true),
  ('C','02',2,'C0202','C0202','STAGING',   null, 200, true,  true),
  ('D','01',1,'D0101','D0101','QUARANTINE',null,  50, false, false),
  ('D','01',2,'D0102','D0102','QUARANTINE',null,  50, false, false)
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
 where s.sku_code = 'SKU-1001' and l.location_code = 'A0101'
on conflict (sku_id, location_id, batch_no, expiry_date) do nothing;

insert into stock_txn
  (txn_no, txn_type, sku_id, location_id, batch_no, expiry_date,
   on_hand_delta, allocated_delta, before_on_hand, after_on_hand,
   ref_type, source, operator_id, remark)
select 'TXN-INIT-0001', 'RECEIPT', s.id, l.id, 'B20261001', date '2027-10-01',
       200, 0, 0, 200, 'MANUAL', 'IMPORT',
       (select id from app_user where username = 'admin'), '期初导入'
  from sku s, location l
 where s.sku_code = 'SKU-1001' and l.location_code = 'A0101'
on conflict (txn_no) do nothing;

-- 自检：应当返回 1 行 OK
-- select recon_status, count(*) from v_inventory_recon group by 1;
