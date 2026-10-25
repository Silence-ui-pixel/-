"""ORM 模型 —— 与 db/schema.sql / alembic 迁移保持一致。

注意：这里只定义 apply_txn 直接依赖的表，不做完整 8 表的映射。
后续业务模块需要更多表时再补，避免一次性把未用到的模型都写出来。

字段口径以 schema.sql 注释为准，任何改动必须先改迁移脚本（alembic），
再同步到这里 —— 迁移脚本是唯一真源。
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 效期哨兵：表示「无固定效期 / 永不失效」。
# 为什么是 9999-12-30 而不是 9999-12-31（date.max）？
# asyncpg 会把 Python date.max(9999-12-31) 序列化成 PG 的 infinity，
# 而 infinity <> date '9999-12-31'，会导致唯一约束维度错配（库存静默算错）。
# date(9999, 12, 30) 是 asyncpg 能正常编码的、语义等价的最大安全日期。
SENTINEL_EXPIRY = date(9999, 12, 30)
SENTINEL_BATCH = ""


class Base(DeclarativeBase):
    """所有模型的基类。"""


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="OPERATOR")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)


class Sku(Base):
    __tablename__ = "sku"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    spec: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_uom: Mapped[str] = mapped_column(String(16), nullable=False, default="EA")
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    volume_m3: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abc_class: Mapped[str | None] = mapped_column(String(1), nullable=True)
    is_batch_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    safety_stock: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    reorder_point: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Location(Base):
    __tablename__ = "location"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    warehouse_code: Mapped[str] = mapped_column(String(32), nullable=False, default="WH01")
    zone_code: Mapped[str] = mapped_column(String(32), nullable=False)
    rack_code: Mapped[str] = mapped_column(String(32), nullable=False)
    level_no: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    bin_code: Mapped[str] = mapped_column(String(32), nullable=False)
    location_code: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    location_type: Mapped[str] = mapped_column(String(16), nullable=False, default="STORAGE")
    pick_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity_qty: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    capacity_volume: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    is_mixed_sku: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_mixed_batch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Inventory(Base):
    """库存余额。唯一维度 sku_id + location_id + batch_no + expiry_date。"""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    expiry_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=SENTINEL_EXPIRY
    )
    qty_on_hand: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    qty_allocated: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    qty_available: Mapped[float] = mapped_column(
        Numeric(14, 3),
        Computed("qty_on_hand - qty_allocated", persisted=True),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StockTxn(Base):
    """库存流水，只追加账本（数据库触发器禁止 UPDATE/DELETE）。"""

    __tablename__ = "stock_txn"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    txn_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    txn_type: Mapped[str] = mapped_column(String(24), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    expiry_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=SENTINEL_EXPIRY
    )
    on_hand_delta: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    allocated_delta: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    before_on_hand: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    after_on_hand: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ref_line_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="SYSTEM")
    agent_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InboundOrder(Base):
    """入库单头。状态机：DRAFT → ARRIVED → RECEIVING → RECEIVED → PUTAWAY → DONE / CANCELLED。"""

    __tablename__ = "inbound_order"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, default="PO")
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    expected_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_expected_qty: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    total_received_qty: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboundOrder(Base):
    """出库单头。状态机：DRAFT → ALLOCATED → PICKING → PICKED → SHIPPED / CANCELLED。"""

    __tablename__ = "outbound_order"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, default="SALE")
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tracking_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_ship_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_qty: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OrderLine(Base):
    """单据明细，入库/出库共用，order_type 判别归属（IN / OUT）。"""

    __tablename__ = "order_line"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    order_type: Mapped[str] = mapped_column(String(3), nullable=False)
    inbound_id: Mapped[int | None] = mapped_column(ForeignKey("inbound_order.id"), nullable=True)
    outbound_id: Mapped[int | None] = mapped_column(ForeignKey("outbound_order.id"), nullable=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    qty_required: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False)
    qty_actual: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    qty_rejected: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    expiry_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=SENTINEL_EXPIRY
    )
    from_location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    to_location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
