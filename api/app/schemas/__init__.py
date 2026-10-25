"""Pydantic 响应/请求模型 —— 与 contracts/openapi.yaml 的 schema 一一对应。

契约是唯一真源：这里每个字段、枚举、默认值都要能对上契约。
改这里必须先改契约（contracts/openapi.yaml），反之亦然。
"""

from datetime import date, datetime
from typing import Literal

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


class SkuCreate(BaseModel):
    """新建商品。sku_code 与 name 必填，其余取默认值。"""

    sku_code: str
    barcode: str | None = None
    name: str
    spec: str | None = None
    category: str | None = None
    base_uom: str = "EA"
    weight_kg: float | None = None
    volume_m3: float | None = None
    shelf_life_days: int | None = None
    abc_class: Literal["A", "B", "C"] | None = None
    is_batch_managed: bool = False
    safety_stock: float = 0
    reorder_point: float = 0


class SkuUpdate(BaseModel):
    """修改商品。字段全部可选，只更新客户端明确提供的字段。

    没有 sku_code / barcode：编码是主数据标识，改了会让历史单据指向错货；
    条码属包装属性，变更需要单独流程（本次契约未开放）。
    """

    name: str | None = None
    spec: str | None = None
    category: str | None = None
    base_uom: str | None = None
    shelf_life_days: int | None = None
    abc_class: Literal["A", "B", "C"] | None = None
    is_batch_managed: bool | None = None
    safety_stock: float | None = None
    reorder_point: float | None = None


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
    spec: str | None = None  # 规格；B 的库存查询页要显示这一列
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


# ---------- 单据：明细 ----------
class OrderLine(BaseModel):
    id: int
    line_no: int
    sku_id: int
    sku_code: str
    sku_name: str
    qty_required: float
    qty_actual: float
    qty_rejected: float
    batch_no: str
    expiry_date: date
    from_location_id: int | None = None
    to_location_id: int | None = None
    status: str


class LineCreate(BaseModel):
    sku_id: int
    qty_required: float


class LineUpdate(BaseModel):
    qty_required: float


# ---------- 单据：入库 ----------
class InboundOrder(ORMModel):
    id: int
    order_no: str
    order_type: str
    supplier_name: str | None = None
    status: str
    expected_at: date | None = None
    received_at: datetime | None = None
    total_expected_qty: float
    total_received_qty: float
    remark: str | None = None
    created_at: datetime
    updated_at: datetime


class InboundOrderCreate(BaseModel):
    order_type: str = "PO"
    supplier_name: str | None = None
    expected_at: date | None = None
    remark: str | None = None
    lines: list[LineCreate]


class InboundOrderDetail(InboundOrder):
    lines: list[OrderLine]


class InboundOrderListResponse(BaseModel):
    items: list[InboundOrder]
    meta: PageMeta


# ---------- 单据：出库 ----------
class OutboundOrder(ORMModel):
    id: int
    order_no: str
    order_type: str
    customer_name: str | None = None
    status: str
    priority: int
    carrier: str | None = None
    tracking_no: str | None = None
    requested_ship_at: date | None = None
    shipped_at: datetime | None = None
    total_qty: float
    remark: str | None = None
    created_at: datetime
    updated_at: datetime


class OutboundOrderCreate(BaseModel):
    order_type: str = "SALE"
    customer_name: str | None = None
    priority: int = 100
    requested_ship_at: date | None = None
    remark: str | None = None
    lines: list[LineCreate]


class OutboundOrderDetail(OutboundOrder):
    lines: list[OrderLine]


class OutboundOrderListResponse(BaseModel):
    items: list[OutboundOrder]
    meta: PageMeta


# ---------- 作业请求（第 3 批：收货/上架/分配/拣货/发运） ----------
class ReceiveLine(BaseModel):
    line_id: int
    qty_actual: float
    qty_rejected: float = 0
    batch_no: str | None = None
    expiry_date: date | None = None


class ReceiveRequest(BaseModel):
    lines: list[ReceiveLine]


class PutawayLine(BaseModel):
    line_id: int
    to_location_id: int | None = None


class PutawayRequest(BaseModel):
    lines: list[PutawayLine] | None = None


class PickConfirmLine(BaseModel):
    line_id: int
    qty_actual: float
    qty_rejected: float = 0


class PickConfirmRequest(BaseModel):
    lines: list[PickConfirmLine]


class ShipRequest(BaseModel):
    carrier: str | None = None
    tracking_no: str | None = None


class PickLine(BaseModel):
    line_id: int
    sku_id: int
    sku_code: str
    sku_name: str
    location_id: int | None = None
    location_code: str
    qty_required: float
    batch_no: str
    expiry_date: date


class PickPlanResponse(BaseModel):
    lines: list[PickLine]


# ---------- AI Agent（P2 实现，本期 501 占位） ----------
# 放在文件末尾是因为 AgentQueryResponse 引用 InventoryItem，
# Python 类定义顺序执行，引用必须先定义。
class AgentQueryRequest(BaseModel):
    query: str


class AgentQueryResponse(BaseModel):
    answer: str
    sql_summary: str | None = None
    data: list[InventoryItem] = []


class AgentSuggestion(BaseModel):
    id: int
    type: Literal["REPLENISH", "TRANSFER"]
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    sku_id: int
    sku_code: str
    suggested_qty: float
    reason: str | None = None
    created_at: datetime
