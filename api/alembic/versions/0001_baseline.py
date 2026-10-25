"""baseline: 核心数据模型 v0.1（8 张表 + 触发器 + 对账视图）

这是系统初始基线，等价于 db/schema.sql 的 DDL 部分（不含种子数据）。
种子数据仍在 db/seed.sql 单独执行（幂等），迁移只负责结构。

三条不可违反的约束（继承自 schema.sql 注释）：
  1) 库存只能通过 stock_service 单一入口写入
  2) 每次库存变动必须同一事务内写一条 stock_txn（带 before/after 快照）
  3) stock_txn 只追加，数据库层禁止 UPDATE / DELETE

Revision ID: 0001
Revises:
Create Date: 2026-10-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- 0. 公共函数：updated_at 自动维护 ----------
    op.execute(
        """
        create or replace function trg_set_updated_at()
        returns trigger as $$
        begin
          new.updated_at = now();
          return new;
        end;
        $$ language plpgsql;
        """
    )

    # ---------- 1. app_user ----------
    op.create_table(
        "app_user",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="OPERATOR"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("username", name="uk_user_username"),
        sa.CheckConstraint("role in ('ADMIN','MANAGER','OPERATOR','VIEWER')", name="ck_user_role"),
        sa.CheckConstraint("status in (0,1)", name="ck_user_status"),
    )
    op.execute("create trigger tg_user_updated_at before update on app_user for each row execute function trg_set_updated_at()")
    op.execute("comment on table app_user is '用户。MVP 用固定角色枚举；P3 再拆 role / permission 表'")
    op.execute("comment on column app_user.role is 'ADMIN 系统管理 / MANAGER 仓管主管 / OPERATOR 作业员 / VIEWER 只读'")

    # ---------- 2. sku ----------
    op.create_table(
        "sku",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("sku_code", sa.String(64), nullable=False),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("spec", sa.String(200), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("base_uom", sa.String(16), nullable=False, server_default="EA"),
        sa.Column("weight_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("volume_m3", sa.Numeric(12, 6), nullable=True),
        sa.Column("shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("abc_class", sa.String(1), nullable=True),
        sa.Column("is_batch_managed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("safety_stock", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("sku_code", name="uk_sku_code"),
        sa.CheckConstraint("abc_class is null or abc_class in ('A','B','C')", name="ck_sku_abc"),
        sa.CheckConstraint("status in (0,1)", name="ck_sku_status"),
        sa.CheckConstraint("safety_stock >= 0 and reorder_point >= 0", name="ck_sku_policy"),
    )
    op.create_index("idx_sku_barcode", "sku", ["barcode"], postgresql_where=sa.text("barcode is not null"))
    op.create_index("idx_sku_status", "sku", ["status"], postgresql_where=sa.text("status = 1"))
    op.execute("create trigger tg_sku_updated_at before update on sku for each row execute function trg_set_updated_at()")
    op.execute("comment on table sku is '商品主数据'")
    op.execute("comment on column sku.is_batch_managed is 'true 时 inbound 明细必须带 batch_no'")
    op.execute("comment on column sku.reorder_point is '补货点，供补货 Agent 与预警使用；真实系统应按仓/时段拆分，MVP 先放这里'")

    # ---------- 3. location ----------
    op.create_table(
        "location",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("warehouse_code", sa.String(32), nullable=False, server_default="WH01"),
        sa.Column("zone_code", sa.String(32), nullable=False),
        sa.Column("rack_code", sa.String(32), nullable=False),
        sa.Column("level_no", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("bin_code", sa.String(32), nullable=False),
        sa.Column("location_code", sa.String(96), nullable=False),
        sa.Column("location_type", sa.String(16), nullable=False, server_default="STORAGE"),
        sa.Column("pick_seq", sa.Integer(), nullable=True),
        sa.Column("capacity_qty", sa.Numeric(14, 3), nullable=True),
        sa.Column("capacity_volume", sa.Numeric(12, 6), nullable=True),
        sa.Column("is_mixed_sku", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_mixed_batch", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("location_code", name="uk_location_code"),
        sa.CheckConstraint("location_type in ('STORAGE','RECEIVING','PICKING','STAGING','QUARANTINE')", name="ck_location_type"),
        sa.CheckConstraint("status in (0,1)", name="ck_location_status"),
    )
    op.create_index("idx_location_pick", "location", ["warehouse_code", "pick_seq"], postgresql_where=sa.text("status = 1"))
    op.create_index("idx_location_zone", "location", ["zone_code", "rack_code"], postgresql_where=sa.text("status = 1"))
    op.execute("create trigger tg_location_updated_at before update on location for each row execute function trg_set_updated_at()")
    op.execute("comment on table location is '库位。编码扁平化，不建父子表'")
    op.execute("comment on column location.pick_seq is '拣货顺序，越小越先拣；生成时按蛇形动线编排'")
    op.execute("comment on column location.location_type is 'STORAGE 存储位 / RECEIVING 收货暂存 / PICKING 拣货位 / STAGING 发货暂存 / QUARANTINE 隔离待检'")

    # ---------- 4. inventory ----------
    op.create_table(
        "inventory",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("sku_id", sa.BigInteger(), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_no", sa.String(64), nullable=False, server_default=""),
        sa.Column("expiry_date", sa.Date(), nullable=False, server_default=sa.text("'9999-12-30'")),
        sa.Column("qty_on_hand", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("qty_allocated", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["sku_id"], ["sku.id"], name="inventory_sku_id_fkey"),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"], name="inventory_location_id_fkey"),
        sa.UniqueConstraint("sku_id", "location_id", "batch_no", "expiry_date", name="uk_inventory_dim"),
        sa.CheckConstraint("qty_on_hand >= 0", name="ck_inv_on_hand"),
        sa.CheckConstraint("qty_allocated >= 0 and qty_allocated <= qty_on_hand", name="ck_inv_allocated"),
    )
    # 生成列 qty_available = qty_on_hand - qty_allocated（不可写）
    op.execute(
        """
        alter table inventory
          add column qty_available numeric(14,3)
          generated always as (qty_on_hand - qty_allocated) stored
        """
    )
    op.create_index("idx_inventory_sku", "inventory", ["sku_id"], postgresql_where=sa.text("qty_on_hand > 0"))
    op.create_index("idx_inventory_loc", "inventory", ["location_id"], postgresql_where=sa.text("qty_on_hand > 0"))
    op.create_index("idx_inventory_expiry", "inventory", ["expiry_date"], postgresql_where=sa.text("expiry_date < '9999-12-30' and qty_on_hand > 0"))
    op.execute("create trigger tg_inventory_updated_at before update on inventory for each row execute function trg_set_updated_at()")
    op.execute("comment on table inventory is '库存余额。唯一写入入口，写必落 stock_txn'")
    op.execute("comment on column inventory.qty_on_hand is '现有量（物理在库）'")
    op.execute("comment on column inventory.qty_allocated is '已分配量（被出库单锁定，未出库）'")
    op.execute("comment on column inventory.qty_available is '可用量 = 现有量 - 已分配量（生成列，不可写）'")
    op.execute("comment on column inventory.version is '乐观锁版本号，并发扣减时用'")

    # ---------- 5. stock_txn ----------
    op.create_table(
        "stock_txn",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("txn_no", sa.String(40), nullable=False),
        sa.Column("txn_type", sa.String(24), nullable=False),
        sa.Column("sku_id", sa.BigInteger(), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_no", sa.String(64), nullable=False, server_default=""),
        sa.Column("expiry_date", sa.Date(), nullable=False, server_default=sa.text("'9999-12-30'")),
        sa.Column("on_hand_delta", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("allocated_delta", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("before_on_hand", sa.Numeric(14, 3), nullable=False),
        sa.Column("after_on_hand", sa.Numeric(14, 3), nullable=False),
        sa.Column("ref_type", sa.String(16), nullable=True),
        sa.Column("ref_id", sa.BigInteger(), nullable=True),
        sa.Column("ref_line_id", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="SYSTEM"),
        sa.Column("agent_run_id", sa.String(64), nullable=True),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["sku_id"], ["sku.id"], name="stock_txn_sku_id_fkey"),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"], name="stock_txn_location_id_fkey"),
        sa.ForeignKeyConstraint(["operator_id"], ["app_user.id"], name="stock_txn_operator_id_fkey"),
        sa.UniqueConstraint("txn_no", name="uk_txn_no"),
        sa.CheckConstraint("txn_type in ('RECEIPT','PUTAWAY','PICK','SHIP','ADJUST','TRANSFER_IN','TRANSFER_OUT','COUNT_ADJUST','ALLOCATE','DEALLOCATE')", name="ck_txn_type"),
        sa.CheckConstraint("source in ('WEB','PDA','AGENT','SYSTEM','IMPORT')", name="ck_txn_source"),
        sa.CheckConstraint("on_hand_delta <> 0 or allocated_delta <> 0", name="ck_txn_delta"),
        sa.CheckConstraint("after_on_hand = before_on_hand + on_hand_delta", name="ck_txn_snapshot"),
    )
    op.create_index("idx_txn_sku_time", "stock_txn", ["sku_id", sa.text("created_at desc")])
    op.create_index("idx_txn_loc_time", "stock_txn", ["location_id", sa.text("created_at desc")])
    op.create_index("idx_txn_ref", "stock_txn", ["ref_type", "ref_id"])
    op.create_index("idx_txn_agent", "stock_txn", ["agent_run_id"], postgresql_where=sa.text("agent_run_id is not null"))
    op.create_index("idx_txn_time", "stock_txn", [sa.text("created_at desc")])
    op.execute("comment on table stock_txn is '库存流水，只追加。禁止 UPDATE / DELETE（有触发器强制）'")
    op.execute("comment on column stock_txn.on_hand_delta is '现有量变化，入库为正、出库为负、分配为 0'")
    op.execute("comment on column stock_txn.allocated_delta is '分配量变化，分配为正、拣货出库为负'")
    op.execute("comment on column stock_txn.agent_run_id is 'AI 链路追溯关键字段：能回答「这单是哪个 Agent 哪次审批产生的」'")
    op.execute("comment on column stock_txn.source is 'WEB 工作台 / PDA / AGENT 智能体 / SYSTEM 系统作业 / IMPORT 导入'")

    # 只追加保护函数 + 触发器
    op.execute(
        """
        create or replace function trg_forbid_mutation()
        returns trigger as $$
        begin
          raise exception 'stock_txn 是只追加账本，禁止 % 操作', tg_op;
        end;
        $$ language plpgsql;
        """
    )
    op.execute("create trigger tg_txn_immutable before update or delete on stock_txn for each row execute function trg_forbid_mutation()")

    # ---------- 6. inbound_order ----------
    op.create_table(
        "inbound_order",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("order_no", sa.String(40), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False, server_default="PO"),
        sa.Column("supplier_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("expected_at", sa.Date(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_expected_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("total_received_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], name="inbound_order_created_by_fkey"),
        sa.UniqueConstraint("order_no", name="uk_inbound_no"),
        sa.CheckConstraint("order_type in ('PO','RETURN','TRANSFER')", name="ck_inbound_type"),
        sa.CheckConstraint("status in ('DRAFT','ARRIVED','RECEIVING','RECEIVED','PUTAWAY','DONE','CANCELLED')", name="ck_inbound_status"),
    )
    op.create_index("idx_inbound_status", "inbound_order", ["status", "expected_at"])
    op.execute("create trigger tg_inbound_updated_at before update on inbound_order for each row execute function trg_set_updated_at()")
    op.execute("comment on table inbound_order is '入库单头。状态机线性推进，回退只能到上一个状态'")
    op.execute("comment on column inbound_order.status is 'DRAFT 草稿 / ARRIVED 已到货 / RECEIVING 收货中 / RECEIVED 收货完成 / PUTAWAY 上架中 / DONE 完结 / CANCELLED 取消'")

    # ---------- 7. outbound_order ----------
    op.create_table(
        "outbound_order",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("order_no", sa.String(40), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False, server_default="SALE"),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="100"),
        sa.Column("carrier", sa.String(64), nullable=True),
        sa.Column("tracking_no", sa.String(64), nullable=True),
        sa.Column("requested_ship_at", sa.Date(), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], name="outbound_order_created_by_fkey"),
        sa.UniqueConstraint("order_no", name="uk_outbound_no"),
        sa.CheckConstraint("order_type in ('SALE','RETURN','TRANSFER')", name="ck_outbound_type"),
        sa.CheckConstraint("status in ('DRAFT','ALLOCATED','PICKING','PICKED','SHIPPED','CANCELLED')", name="ck_outbound_status"),
    )
    op.create_index("idx_outbound_status", "outbound_order", ["status", "priority", "requested_ship_at"])
    op.execute("create trigger tg_outbound_updated_at before update on outbound_order for each row execute function trg_set_updated_at()")
    op.execute("comment on table outbound_order is '出库单头'")
    op.execute("comment on column outbound_order.status is 'DRAFT 草稿 / ALLOCATED 已分配库存 / PICKING 拣货中 / PICKED 已拣 / SHIPPED 已发运 / CANCELLED 取消'")
    op.execute("comment on column outbound_order.priority is '优先级，AI 与规则都可调；越小越优先'")

    # ---------- 8. order_line ----------
    op.create_table(
        "order_line",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("order_type", sa.String(3), nullable=False),
        sa.Column("inbound_id", sa.BigInteger(), nullable=True),
        sa.Column("outbound_id", sa.BigInteger(), nullable=True),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.BigInteger(), nullable=False),
        sa.Column("qty_required", sa.Numeric(14, 3), nullable=False),
        sa.Column("qty_actual", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("qty_rejected", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("batch_no", sa.String(64), nullable=False, server_default=""),
        sa.Column("expiry_date", sa.Date(), nullable=False, server_default=sa.text("'9999-12-30'")),
        sa.Column("from_location_id", sa.BigInteger(), nullable=True),
        sa.Column("to_location_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("remark", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["inbound_id"], ["inbound_order.id"], name="order_line_inbound_id_fkey"),
        sa.ForeignKeyConstraint(["outbound_id"], ["outbound_order.id"], name="order_line_outbound_id_fkey"),
        sa.ForeignKeyConstraint(["sku_id"], ["sku.id"], name="order_line_sku_id_fkey"),
        sa.ForeignKeyConstraint(["from_location_id"], ["location.id"], name="order_line_from_location_id_fkey"),
        sa.ForeignKeyConstraint(["to_location_id"], ["location.id"], name="order_line_to_location_id_fkey"),
        sa.CheckConstraint("(order_type = 'IN' and inbound_id is not null and outbound_id is null) or (order_type = 'OUT' and outbound_id is not null and inbound_id is null)", name="ck_line_owner"),
        sa.CheckConstraint("order_type in ('IN','OUT')", name="ck_line_type"),
        sa.CheckConstraint("status in ('OPEN','ALLOCATED','PARTIAL','DONE','CANCELLED')", name="ck_line_status"),
        sa.CheckConstraint("qty_required > 0 and qty_actual >= 0 and qty_rejected >= 0", name="ck_line_qty"),
        sa.CheckConstraint("order_type = 'IN' or qty_actual <= qty_required + 0.0001", name="ck_line_out_qty"),
    )
    op.create_index("uk_line_inbound", "order_line", ["inbound_id", "line_no"], unique=True, postgresql_where=sa.text("inbound_id is not null"))
    op.create_index("uk_line_outbound", "order_line", ["outbound_id", "line_no"], unique=True, postgresql_where=sa.text("outbound_id is not null"))
    op.create_index("idx_line_sku", "order_line", ["sku_id", "status"])
    op.execute("create trigger tg_line_updated_at before update on order_line for each row execute function trg_set_updated_at()")
    op.execute("comment on table order_line is '单据明细，入库与出库共用；order_type 判别归属'")
    op.execute("comment on column order_line.status is 'OPEN 待处理 / ALLOCATED 已分配 / PARTIAL 部分完成 / DONE 完成 / CANCELLED 取消'")

    # ---------- 9. 对账视图 ----------
    op.execute(
        """
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
            when i.id is null then 'ONLY_TXN'
            when t.sku_id is null then 'ONLY_INVENTORY'
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
        """
    )
    op.execute("comment on view v_inventory_recon is '库存对账视图：inv 余额 与 流水累计 比对，recon_status <> OK 即异常'")


def downgrade() -> None:
    op.execute("drop view if exists v_inventory_recon")
    op.drop_table("order_line")
    op.drop_table("outbound_order")
    op.drop_table("inbound_order")
    op.drop_table("stock_txn")
    op.drop_table("inventory")
    op.drop_table("location")
    op.drop_table("sku")
    op.drop_table("app_user")
    op.execute("drop function if exists trg_forbid_mutation()")
    op.execute("drop function if exists trg_set_updated_at()")
