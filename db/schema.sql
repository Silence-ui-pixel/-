-- =============================================================================
-- 仓储智能管理 Agent 系统 · 核心数据模型 v0.1
-- 目标数据库: PostgreSQL 16+
--
-- 三条不可违反的约束（后续所有代码必须遵守）:
--   1) 库存只能通过 stock_service 单一入口写入，禁止任何地方直接 UPDATE inventory
--   2) 每次库存变动必须在同一事务内写入一条 stock_txn（带 before/after 快照）
--   3) stock_txn 是只追加账本，数据库层面禁止 UPDATE / DELETE
--
-- 表清单（8 张）:
--   app_user        用户
--   sku             商品主数据
--   location        库位
--   inventory       库存余额（唯一写入点）
--   stock_txn       库存流水（只追加）
--   inbound_order   入库单头
--   outbound_order  出库单头
--   order_line      单据明细（入库/出库共用，多态归属）
-- =============================================================================

-- =============================================================================
-- 0. 公共：updated_at 自动维护
-- =============================================================================
create or replace function trg_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;


-- =============================================================================
-- 1. app_user  用户
--    先建这张表，供后续单据 / 流水引用
-- =============================================================================
create table app_user (
  id             bigserial     primary key,
  username       varchar(64)   not null,
  display_name   varchar(64)   not null,
  password_hash  varchar(200)  not null,
  role           varchar(16)   not null default 'OPERATOR',
  status         smallint      not null default 1,          -- 1 启用 / 0 停用
  last_login_at  timestamptz,
  created_at     timestamptz   not null default now(),
  updated_at     timestamptz   not null default now(),
  constraint uk_user_username unique (username),
  constraint ck_user_role     check (role in ('ADMIN','MANAGER','OPERATOR','VIEWER')),
  constraint ck_user_status   check (status in (0,1))
);
comment on table  app_user      is '用户。MVP 用固定角色枚举；P3 再拆 role / permission 表';
comment on column app_user.role is 'ADMIN 系统管理 / MANAGER 仓管主管 / OPERATOR 作业员 / VIEWER 只读';

create trigger tg_user_updated_at before update on app_user
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 2. sku  商品主数据
-- =============================================================================
create table sku (
  id                bigserial     primary key,
  sku_code          varchar(64)   not null,
  barcode           varchar(64),
  name              varchar(200)  not null,
  spec              varchar(200),
  category          varchar(64),
  base_uom          varchar(16)   not null default 'EA',
  weight_kg         numeric(10,3),
  volume_m3         numeric(12,6),
  shelf_life_days   integer,                                 -- null = 不管理效期
  abc_class         char(1),                                 -- 库位策略用
  is_batch_managed  boolean       not null default false,
  safety_stock      numeric(14,3) not null default 0,
  reorder_point     numeric(14,3) not null default 0,
  status            smallint      not null default 1,
  created_at        timestamptz   not null default now(),
  updated_at        timestamptz   not null default now(),
  constraint uk_sku_code    unique (sku_code),
  constraint ck_sku_abc     check (abc_class is null or abc_class in ('A','B','C')),
  constraint ck_sku_status  check (status in (0,1)),
  constraint ck_sku_policy  check (safety_stock >= 0 and reorder_point >= 0)
);
comment on table  sku                   is '商品主数据';
comment on column sku.is_batch_managed  is 'true 时 inbound 明细必须带 batch_no';
comment on column sku.reorder_point     is '补货点，供补货 Agent 与预警使用；真实系统应按仓/时段拆分，MVP 先放这里';

create index idx_sku_barcode on sku (barcode) where barcode is not null;
create index idx_sku_status  on sku (status)  where status = 1;

create trigger tg_sku_updated_at before update on sku
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 3. location  库位
--    刻意不做 parent_id 递归：仓储层级固定为 仓/区/架/层/位，用扁平冗余列
--    更简单、查询更快，且便于按 pick_seq 做拣货路径排序
-- =============================================================================
create table location (
  id                bigserial     primary key,
  warehouse_code    varchar(32)   not null default 'WH01',
  zone_code         varchar(32)   not null,                  -- 库区  A / B / COLD
  rack_code         varchar(32)   not null,                  -- 货架  01
  level_no          smallint      not null default 1,        -- 层    1..N
  bin_code          varchar(32)   not null,                  -- 位    03
  location_code     varchar(96)   not null,                  -- 全码  WH01-A-01-03
  location_type     varchar(16)   not null default 'STORAGE',
  pick_seq          integer,                                 -- 拣货顺序号（蛇形排布）
  capacity_qty      numeric(14,3),
  capacity_volume   numeric(12,6),
  is_mixed_sku      boolean       not null default true,     -- 是否允许混放不同 SKU
  is_mixed_batch    boolean       not null default true,     -- 是否允许混放不同批次
  status            smallint      not null default 1,
  created_at        timestamptz   not null default now(),
  updated_at        timestamptz   not null default now(),
  constraint uk_location_code unique (location_code),
  constraint ck_location_type check (location_type in
    ('STORAGE','RECEIVING','PICKING','STAGING','QUARANTINE')),
  constraint ck_location_status check (status in (0,1))
);
comment on table  location               is '库位。编码扁平化，不建父子表';
comment on column location.pick_seq      is '拣货顺序，越小越先拣；生成时按蛇形动线编排';
comment on column location.location_type is 'STORAGE 存储位 / RECEIVING 收货暂存 / PICKING 拣货位 / STAGING 发货暂存 / QUARANTINE 隔离待检';

create index idx_location_pick  on location (warehouse_code, pick_seq) where status = 1;
create index idx_location_zone  on location (zone_code, rack_code)      where status = 1;

create trigger tg_location_updated_at before update on location
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 4. inventory  库存余额（全系统唯一写入点）
--
--    唯一维度: sku_id + location_id + batch_no + expiry_date
--    关键技巧: batch_no 用空串、expiry_date 用哨兵日期 9999-12-31
--             因为在 PostgreSQL 中 NULL <> NULL，若允许 NULL 则唯一约束会失效，
--             同一维度会被重复插入多行，库存直接算错。
-- =============================================================================
create table inventory (
  id             bigserial     primary key,
  sku_id         bigint        not null references sku(id),
  location_id    bigint        not null references location(id),
  batch_no       varchar(64)   not null default '',
  expiry_date    date          not null default '9999-12-31',
  qty_on_hand    numeric(14,3) not null default 0,
  qty_allocated  numeric(14,3) not null default 0,
  qty_available  numeric(14,3) generated always as (qty_on_hand - qty_allocated) stored,
  version        bigint        not null default 0,           -- 乐观锁
  updated_at     timestamptz   not null default now(),
  constraint uk_inventory_dim  unique (sku_id, location_id, batch_no, expiry_date),
  constraint ck_inv_on_hand    check (qty_on_hand >= 0),
  constraint ck_inv_allocated  check (qty_allocated >= 0 and qty_allocated <= qty_on_hand)
);
comment on table  inventory               is '库存余额。唯一写入入口，写必落 stock_txn';
comment on column inventory.qty_on_hand   is '现有量（物理在库）';
comment on column inventory.qty_allocated is '已分配量（被出库单锁定，未出库）';
comment on column inventory.qty_available is '可用量 = 现有量 - 已分配量（生成列，不可写）';
comment on column inventory.version       is '乐观锁版本号，并发扣减时用';

create index idx_inventory_sku    on inventory (sku_id) where qty_on_hand > 0;
create index idx_inventory_loc    on inventory (location_id) where qty_on_hand > 0;
create index idx_inventory_expiry on inventory (expiry_date)
  where expiry_date < '9999-12-31' and qty_on_hand > 0;

create trigger tg_inventory_updated_at before update on inventory
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 5. stock_txn  库存流水（只追加账本）
--
--    设计要点: 用 on_hand_delta / allocated_delta 两个变更量，
--    而不是单一 qty + direction。因为「分配」只动 allocated 不动 on_hand，
--    单列无法表达这种变动，会导致对账时 SUM 不等于余额。
-- =============================================================================
create table stock_txn (
  id               bigserial     primary key,
  txn_no           varchar(40)   not null,
  txn_type         varchar(24)   not null,
  sku_id           bigint        not null references sku(id),
  location_id      bigint        not null references location(id),
  batch_no         varchar(64)   not null default '',
  expiry_date      date          not null default '9999-12-31',
  on_hand_delta    numeric(14,3) not null default 0,         -- 现有量变化，
  allocated_delta  numeric(14,3) not null default 0,         -- 分配量变化
  before_on_hand   numeric(14,3) not null,
  after_on_hand    numeric(14,3) not null,
  ref_type         varchar(16),                              -- INBOUND / OUTBOUND / COUNT / MANUAL
  ref_id           bigint,
  ref_line_id      bigint,
  source           varchar(16)   not null default 'SYSTEM',
  agent_run_id     varchar(64),                              -- AI 发起时的会话/审批单 ID
  operator_id      bigint        references app_user(id),
  remark           varchar(500),
  created_at       timestamptz   not null default now(),
  constraint uk_txn_no        unique (txn_no),
  constraint ck_txn_type      check (txn_type in (
    'RECEIPT','PUTAWAY','PICK','SHIP','ADJUST',
    'TRANSFER_IN','TRANSFER_OUT','COUNT_ADJUST','ALLOCATE','DEALLOCATE')),
  constraint ck_txn_source    check (source in ('WEB','PDA','AGENT','SYSTEM','IMPORT')),
  constraint ck_txn_delta     check (on_hand_delta <> 0 or allocated_delta <> 0),
  constraint ck_txn_snapshot  check (after_on_hand = before_on_hand + on_hand_delta)
);
comment on table  stock_txn                 is '库存流水，只追加。禁止 UPDATE / DELETE（有触发器强制）';
comment on column stock_txn.on_hand_delta   is '现有量变化，入库为正、出库为负、分配为 0';
comment on column stock_txn.allocated_delta is '分配量变化，分配为正、拣货出库为负';
comment on column stock_txn.agent_run_id    is 'AI 链路追溯关键字段：能回答「这单是哪个 Agent 哪次审批产生的」';
comment on column stock_txn.source          is 'WEB 工作台 / PDA / AGENT 智能体 / SYSTEM 系统作业 / IMPORT 导入';

create index idx_txn_sku_time on stock_txn (sku_id, created_at desc);
create index idx_txn_loc_time on stock_txn (location_id, created_at desc);
create index idx_txn_ref      on stock_txn (ref_type, ref_id);
create index idx_txn_agent    on stock_txn (agent_run_id) where agent_run_id is not null;
create index idx_txn_time     on stock_txn (created_at desc);

-- 数据库层面强制只追加
create or replace function trg_forbid_mutation()
returns trigger as $$
begin
  raise exception 'stock_txn 是只追加账本，禁止 % 操作', tg_op;
end;
$$ language plpgsql;

create trigger tg_txn_immutable
  before update or delete on stock_txn
  for each row execute function trg_forbid_mutation();


-- =============================================================================
-- 6. inbound_order  入库单头
-- =============================================================================
create table inbound_order (
  id                  bigserial     primary key,
  order_no            varchar(40)   not null,
  order_type          varchar(16)   not null default 'PO',
  supplier_name       varchar(200),
  status              varchar(20)   not null default 'DRAFT',
  expected_at         date,
  received_at         timestamptz,
  total_expected_qty  numeric(14,3) not null default 0,
  total_received_qty  numeric(14,3) not null default 0,
  remark              varchar(500),
  created_by          bigint        references app_user(id),
  version             bigint        not null default 0,
  created_at          timestamptz   not null default now(),
  updated_at          timestamptz   not null default now(),
  constraint uk_inbound_no      unique (order_no),
  constraint ck_inbound_type    check (order_type in ('PO','RETURN','TRANSFER')),
  constraint ck_inbound_status  check (status in
    ('DRAFT','ARRIVED','RECEIVING','RECEIVED','PUTAWAY','DONE','CANCELLED'))
);
comment on table  inbound_order        is '入库单头。状态机线性推进，回退只能到上一个状态';
comment on column inbound_order.status is 'DRAFT 草稿 / ARRIVED 已到货 / RECEIVING 收货中 / RECEIVED 收货完成 / PUTAWAY 上架中 / DONE 完结 / CANCELLED 取消';

create index idx_inbound_status on inbound_order (status, expected_at);

create trigger tg_inbound_updated_at before update on inbound_order
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 7. outbound_order  出库单头
-- =============================================================================
create table outbound_order (
  id               bigserial     primary key,
  order_no         varchar(40)   not null,
  order_type       varchar(16)   not null default 'SALE',
  customer_name    varchar(200),
  status           varchar(20)   not null default 'DRAFT',
  priority         smallint      not null default 100,       -- 越小越优先
  carrier          varchar(64),
  tracking_no      varchar(64),
  requested_ship_at date,
  shipped_at       timestamptz,
  total_qty        numeric(14,3) not null default 0,
  remark           varchar(500),
  created_by       bigint        references app_user(id),
  version          bigint        not null default 0,
  created_at       timestamptz   not null default now(),
  updated_at       timestamptz   not null default now(),
  constraint uk_outbound_no      unique (order_no),
  constraint ck_outbound_type    check (order_type in ('SALE','RETURN','TRANSFER')),
  constraint ck_outbound_status  check (status in
    ('DRAFT','ALLOCATED','PICKING','PICKED','SHIPPED','CANCELLED'))
);
comment on table  outbound_order          is '出库单头';
comment on column outbound_order.status   is 'DRAFT 草稿 / ALLOCATED 已分配库存 / PICKING 拣货中 / PICKED 已拣 / SHIPPED 已发运 / CANCELLED 取消';
comment on column outbound_order.priority is '优先级，AI 与规则都可调；越小越优先';

create index idx_outbound_status on outbound_order (status, priority, requested_ship_at);

create trigger tg_outbound_updated_at before update on outbound_order
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 8. order_line  单据明细（入库 / 出库共用）
--
--    多态归属用「判别列 + 两个可空外键 + CHECK 约束」实现，
--    保留外键完整性的同时避免拆成两张几乎一样的表。
--    唯一性用部分唯一索引解决（可空列不能进普通 UNIQUE 约束）。
-- =============================================================================
create table order_line (
  id                bigserial     primary key,
  order_type        char(2)       not null,                  -- IN / OUT
  inbound_id        bigint        references inbound_order(id),
  outbound_id       bigint        references outbound_order(id),
  line_no           integer       not null,
  sku_id            bigint        not null references sku(id),
  qty_required      numeric(14,3) not null,                  -- 应收 / 应拣
  qty_actual        numeric(14,3) not null default 0,        -- 实收 / 实拣
  qty_rejected      numeric(14,3) not null default 0,        -- 不良 / 短拣
  batch_no          varchar(64)   not null default '',
  expiry_date       date          not null default '9999-12-31',
  from_location_id  bigint        references location(id),   -- 出库: 拣货库位
  to_location_id    bigint        references location(id),   -- 入库: 上架库位
  status            varchar(16)   not null default 'OPEN',
  remark            varchar(500),
  created_at        timestamptz   not null default now(),
  updated_at        timestamptz   not null default now(),
  constraint ck_line_owner  check (
    (order_type = 'IN'  and inbound_id  is not null and outbound_id is null) or
    (order_type = 'OUT' and outbound_id is not null and inbound_id  is null)
  ),
  constraint ck_line_type   check (order_type in ('IN','OUT')),
  constraint ck_line_status check (status in
    ('OPEN','ALLOCATED','PARTIAL','DONE','CANCELLED')),
  constraint ck_line_qty    check (
    qty_required > 0 and qty_actual >= 0 and qty_rejected >= 0
  ),
  -- 允许入库超收（供应商多发），出库不允许超拣
  constraint ck_line_out_qty check (
    order_type = 'IN' or qty_actual <= qty_required + 0.0001
  )
);
comment on table  order_line      is '单据明细，入库与出库共用；order_type 判别归属';
comment on column order_line.status is 'OPEN 待处理 / ALLOCATED 已分配 / PARTIAL 部分完成 / DONE 完成 / CANCELLED 取消';

create unique index uk_line_inbound  on order_line (inbound_id,  line_no) where inbound_id  is not null;
create unique index uk_line_outbound on order_line (outbound_id, line_no) where outbound_id is not null;
create index        idx_line_sku     on order_line (sku_id, status);

create trigger tg_line_updated_at before update on order_line
  for each row execute function trg_set_updated_at();


-- =============================================================================
-- 9. 对账视图：库存余额 vs 流水累计
--    用途: 每日定时跑，任何一行出现差异即告警。
--    这是「账实一致」的技术保障，不是可选优化。
-- =============================================================================
create or replace view v_inventory_recon as
with txn_agg as (
  select sku_id, location_id, batch_no, expiry_date,
         sum(on_hand_delta)   as txn_on_hand,
         sum(allocated_delta) as txn_allocated,
         count(*)             as txn_count
    from stock_txn
   group by sku_id, location_id, batch_no, expiry_date
)
select
  coalesce(i.sku_id,      t.sku_id)      as sku_id,
  coalesce(i.location_id, t.location_id) as location_id,
  coalesce(i.batch_no,    t.batch_no)    as batch_no,
  coalesce(i.expiry_date, t.expiry_date) as expiry_date,
  coalesce(i.qty_on_hand,   0)           as inv_on_hand,
  coalesce(t.txn_on_hand,   0)           as txn_on_hand,
  coalesce(i.qty_allocated, 0)           as inv_allocated,
  coalesce(t.txn_allocated, 0)           as txn_allocated,
  coalesce(i.qty_on_hand, 0)   - coalesce(t.txn_on_hand, 0)   as diff_on_hand,
  coalesce(i.qty_allocated, 0) - coalesce(t.txn_allocated, 0) as diff_allocated,
  coalesce(t.txn_count, 0)               as txn_count,
  case
    when i.id is null then 'ONLY_TXN'          -- 有流水无余额行，说明漏建 inventory
    when t.sku_id is null then 'ONLY_INVENTORY'-- 有余额无流水，说明有人绕过入口直接改
    when abs(coalesce(i.qty_on_hand,0) - coalesce(t.txn_on_hand,0)) > 0.0001
      or abs(coalesce(i.qty_allocated,0) - coalesce(t.txn_allocated,0)) > 0.0001
      then 'MISMATCH'
    else 'OK'
  end as recon_status
from inventory i
full outer join txn_agg t
  on  t.sku_id = i.sku_id
  and t.location_id = i.location_id
  and t.batch_no = i.batch_no
  and t.expiry_date = i.expiry_date;

comment on view v_inventory_recon is '库存对账视图：inv 余额 与 流水累计 比对，recon_status <> OK 即异常';


-- =============================================================================
-- 10. 种子数据已拆分到 db/seed.sql
--
--     原因: DDL 只该跑一次，种子数据要能反复跑（本地开发 / CI 建库 /
--     演示环境重建都会重跑）。混在一个文件里，就只能二选一：
--       要么整个文件不可重跑  → 现在的问题
--       要么 DDL 改成 create table if not exists → 掩盖结构不一致，更危险
--
--     执行顺序：
--       psql -f db/schema.sql    建结构（一次）
--       psql -f db/seed.sql      播种（可重复）
--
--     接入 alembic 后（S1-06），迁移只覆盖本文件的 DDL，seed 单独调用。
-- =============================================================================

-- 建完结构后自检：应当返回 0 行
-- select * from v_inventory_recon where recon_status <> 'OK';

