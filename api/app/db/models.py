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
    Numeric,
    String,
    func,
    literal_column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

# 效期哨兵。核心问题：asyncpg 会把 Python date.max(9999-12-31) 序列化成
# PG 的 infinity，而 schema.sql 里用的是字面量 date '9999-12-31'，两者不相等，
# 会导致 uk_inventory_dim 唯一约束维度错配（库存算错）。
# 因此用 SentinelDate 类型：绑定参数时把 date.max 内联成 SQL 字面量。
SENTINEL_EXPIRY = "9999-12-31"
SENTINEL_BATCH = ""


class SentinelDate(TypeDecorator):
    """Date 变体：date.max 内联为字面量 date '9999-12-31'，避开 asyncpg 的 infinity 映射。"""

    impl = Date
    cache_ok = True

    def bind_expression(self, bindvalue):
        from sqlalchemy import case

        # 当绑定值是 date.max 时，返回字面量 date '9999-12-31'；否则原样
        return case(
            (bindvalue == date.max, literal_column("date '9999-12-31'")),
            else_=bindvalue,
        )


class Base(DeclarativeBase):
    """所有模型的基类。"""


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="OPERATOR")


class Sku(Base):
    __tablename__ = "sku"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_uom: Mapped[str] = mapped_column(String(16), nullable=False, default="EA")
    is_batch_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Location(Base):
    __tablename__ = "location"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    location_code: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    location_type: Mapped[str] = mapped_column(String(16), nullable=False, default="STORAGE")


class Inventory(Base):
    """库存余额。唯一维度 sku_id + location_id + batch_no + expiry_date。"""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), nullable=False)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    expiry_date: Mapped[date] = mapped_column(
        SentinelDate(), nullable=False, default=date.max
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
        SentinelDate(), nullable=False, default=date.max
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
