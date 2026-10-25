// =============================================================================
// 从 db/schema(1).sql 反推的领域类型（临时占位）
// 说明：等 A 产出 openapi.yaml 后，用 `npm run gen` 生成的正式类型覆盖本文件。
// 字段口径以 schema.sql 注释为准。
// =============================================================================

/** 用户角色枚举（权限由低到高：VIEWER < OPERATOR < MANAGER < ADMIN） */
export type UserRole = 'ADMIN' | 'MANAGER' | 'OPERATOR' | 'VIEWER'

/**
 * 路由 meta 元信息（vue-router 使用）
 * 说明：前端权限仅做「体验拦截」（隐藏菜单 / 拦截跳转），最终鉴权由后端 A 兜底。
 */
export interface AppRouteMeta {
  /** 页面标题（侧边菜单 + 顶栏显示） */
  title: string
  /** Element Plus 图标名（可选） */
  icon?: string
  /** 菜单排序，数字越小越靠前 */
  sort?: number
  /** 是否在侧边菜单隐藏（true 则不显示，但仍可通过路由访问） */
  hidden?: boolean
  /** 可访问该页面的角色列表；缺省表示所有登录用户可见 */
  roles?: UserRole[]
  /** 是否缓存页面（keep-alive） */
  keepAlive?: boolean
  /** 是否为公开页（无需登录即可访问，如登录页） */
  public?: boolean
}

/** 用户 */
export interface AppUser {
  id: number
  username: string
  displayName: string
  role: UserRole
  status: 0 | 1
  lastLoginAt?: string
  createdAt: string
  updatedAt: string
}

/** 商品主数据 */
export interface Sku {
  id: number
  skuCode: string
  barcode?: string
  name: string
  spec?: string
  category?: string
  baseUom: string
  weightKg?: number
  volumeM3?: number
  shelfLifeDays?: number
  abcClass?: 'A' | 'B' | 'C'
  isBatchManaged: boolean
  safetyStock: number
  reorderPoint: number
  status: 0 | 1
  createdAt: string
  updatedAt: string
}

/** 库位类型 */
export type LocationType = 'STORAGE' | 'RECEIVING' | 'PICKING' | 'STAGING' | 'QUARANTINE'

/** 库位 */
export interface Location {
  id: number
  warehouseCode: string
  zoneCode: string
  rackCode: string
  levelNo: number
  binCode: string
  locationCode: string
  locationType: LocationType
  pickSeq?: number
  capacityQty?: number
  capacityVolume?: number
  isMixedSku: boolean
  isMixedBatch: boolean
  status: 0 | 1
  createdAt: string
  updatedAt: string
}

/**
 * 库存余额
 * 注意：qtyAvailable 是数据库生成列（generated always as ... stored），只读，前端禁止反算后提交。
 */
export interface Inventory {
  id: number
  skuId: number
  locationId: number
  batchNo: string
  expiryDate: string
  /** 现有量（物理在库） */
  qtyOnHand: number
  /** 已分配量（被出库单锁定，未出库） */
  qtyAllocated: number
  /** 可用量 = 现有量 - 已分配量（只读） */
  qtyAvailable: number
  version: number
  updatedAt: string
}

/** 库存流水类型 */
export type TxnType =
  | 'RECEIPT'
  | 'PUTAWAY'
  | 'PICK'
  | 'SHIP'
  | 'ADJUST'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT'
  | 'COUNT_ADJUST'
  | 'ALLOCATE'
  | 'DEALLOCATE'

/** 流水来源 */
export type TxnSource = 'WEB' | 'PDA' | 'AGENT' | 'SYSTEM' | 'IMPORT'

/** 库存流水（只追加账本） */
export interface StockTxn {
  id: number
  txnNo: string
  txnType: TxnType
  skuId: number
  locationId: number
  batchNo: string
  expiryDate: string
  onHandDelta: number
  allocatedDelta: number
  beforeOnHand: number
  afterOnHand: number
  refType?: string
  refId?: number
  refLineId?: number
  source: TxnSource
  agentRunId?: string
  operatorId?: number
  remark?: string
  createdAt: string
}

/** 入库单状态 */
export type InboundStatus =
  | 'DRAFT'
  | 'ARRIVED'
  | 'RECEIVING'
  | 'RECEIVED'
  | 'PUTAWAY'
  | 'DONE'
  | 'CANCELLED'

/** 入库单头 */
export interface InboundOrder {
  id: number
  orderNo: string
  orderType: 'PO' | 'RETURN' | 'TRANSFER'
  supplierName?: string
  status: InboundStatus
  expectedAt?: string
  receivedAt?: string
  totalExpectedQty: number
  totalReceivedQty: number
  remark?: string
  createdBy?: number
  version: number
  createdAt: string
  updatedAt: string
}

/** 出库单状态 */
export type OutboundStatus = 'DRAFT' | 'ALLOCATED' | 'PICKING' | 'PICKED' | 'SHIPPED' | 'CANCELLED'

/** 出库单头 */
export interface OutboundOrder {
  id: number
  orderNo: string
  orderType: 'SALE' | 'RETURN' | 'TRANSFER'
  customerName?: string
  status: OutboundStatus
  priority: number
  carrier?: string
  trackingNo?: string
  requestedShipAt?: string
  shippedAt?: string
  totalQty: number
  remark?: string
  createdBy?: number
  version: number
  createdAt: string
  updatedAt: string
}

/** 单据明细状态 */
export type LineStatus = 'OPEN' | 'ALLOCATED' | 'PARTIAL' | 'DONE' | 'CANCELLED'

/** 单据明细（入库 / 出库共用，orderType 判别归属） */
export interface OrderLine {
  id: number
  orderType: 'IN' | 'OUT'
  inboundId?: number
  outboundId?: number
  lineNo: number
  skuId: number
  qtyRequired: number
  qtyActual: number
  qtyRejected: number
  batchNo: string
  expiryDate: string
  fromLocationId?: number
  toLocationId?: number
  status: LineStatus
  remark?: string
  createdAt: string
  updatedAt: string
}

// =============================================================================
// 视图 / 组合类型（前端展示用，非数据库表）
// =============================================================================

/** 库存查询页：inventory 联 sku / location 后的展示行 */
export interface InventoryRow extends Inventory {
  skuCode: string
  skuName: string
  barcode?: string
  baseUom: string
  locationCode: string
  zoneCode: string
  isBatchManaged: boolean
}

/** 通用分页响应 */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}
