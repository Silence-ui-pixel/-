"""Pydantic 响应/请求模型 —— 与 contracts/openapi.yaml 的 schema 一一对应。

契约是唯一真源：这里每个字段、枚举、默认值都要能对上契约。
改这里必须先改契约（contracts/openapi.yaml），反之亦然。
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """从 ORM 对象构造的通用配置。"""

    model_config = ConfigDict(from_attributes=True)


# ---------- 通用 ----------
class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


# ---------- 商品 ----------
class Sku(ORMModel):
    id: int
    sku_code: str
    barcode: str | None = None
    name: str
    spec: str | None = None
    category: str | None = None
    base_uom: str
    weight_kg: float | None = None
    volume_m3: float | None = None
    shelf_life_days: int | None = None
    abc_class: str | None = None
    is_batch_managed: bool
    safety_stock: float
    reorder_point: float
    status: int
    created_at: datetime
    updated_at: datetime


class SkuListResponse(BaseModel):
    items: list[Sku]
    meta: PageMeta


# ---------- 库位 ----------
class Location(ORMModel):
    id: int
    warehouse_code: str
    zone_code: str
    rack_code: str
    level_no: int
    bin_code: str
    location_code: str
    location_type: str
    pick_seq: int | None = None
    status: int


class LocationListResponse(BaseModel):
    items: list[Location]


# ---------- 库存 ----------
class InventoryItem(BaseModel):
    sku_id: int
    sku_code: str
    sku_name: str
    location_id: int
    location_code: str
    location_type: str
    batch_no: str
    expiry_date: date
    qty_on_hand: float
    qty_allocated: float
    qty_available: float
    base_uom: str


class InventoryListResponse(BaseModel):
    items: list[InventoryItem]
    meta: PageMeta


class StockTxnItem(ORMModel):
    id: int
    txn_no: str
    txn_type: str
    sku_id: int
    sku_code: str
    location_code: str
    batch_no: str
    expiry_date: date
    on_hand_delta: float
    allocated_delta: float
    before_on_hand: float
    after_on_hand: float
    ref_type: str | None = None
    ref_id: int | None = None
    source: str
    agent_run_id: str | None = None
    operator_id: int | None = None
    remark: str | None = None
    created_at: datetime


class StockTxnListResponse(BaseModel):
    items: list[StockTxnItem]
    meta: PageMeta


class ReconItem(BaseModel):
    sku_id: int | None = None
    location_id: int | None = None
    batch_no: str
    expiry_date: date
    inv_on_hand: float
    txn_on_hand: float
    diff_on_hand: float
    recon_status: str


class ReconResponse(BaseModel):
    items: list[ReconItem]
