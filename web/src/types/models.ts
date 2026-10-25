// =============================================================================
// 类型定义统一出口
// -----------------------------------------------------------------------------
// 本文件分两部分：
//   1. 后端业务模型：来自 OpenAPI 契约（contracts/openapi.yaml），经
//      openapi-typescript 生成于 `src/api/schema.d.ts`，这里具名 re-export，
//      业务代码统一从这里 import。契约冻结后「只增字段、不改语义」。
//      字段为 snake_case（与数据库列名一致），多为可选（?）。
//   2. 前端专属类型：UserRole、AppRouteMeta（路由 / 权限），不属于后端契约，
//      保留手写，不随契约生成。
//
// 重新生成契约类型：`npm run gen:api`（契约变更由 A 通知后再执行）。
// =============================================================================

import type { components } from '@/api/schema'

type Schema = components['schemas']

// ---------------------------------------------------------------------------
// 1. 后端契约 schema（具名 re-export）
// ---------------------------------------------------------------------------

/** 统一错误响应 { code, message, detail }（契约原名 Error，此处避免与全局 Error 混淆） */
export type ApiError = Schema['Error']
/** 分页元信息 { total, page, page_size } */
export type PageMeta = Schema['PageMeta']

export type LoginRequest = Schema['LoginRequest']
export type LoginResponse = Schema['LoginResponse']

/** 用户（role 与下方 UserRole 值域一致） */
export type User = Schema['User']

export type Sku = Schema['Sku']
export type SkuCreate = Schema['SkuCreate']
export type SkuUpdate = Schema['SkuUpdate']
export type SkuListResponse = Schema['SkuListResponse']

export type Location = Schema['Location']
export type LocationListResponse = Schema['LocationListResponse']

/** 库存余额（含 sku/location 联表展示字段；qty_available 为生成列，只读） */
export type InventoryItem = Schema['InventoryItem']
export type InventoryListResponse = Schema['InventoryListResponse']

export type StockTxnItem = Schema['StockTxnItem']
export type StockTxnListResponse = Schema['StockTxnListResponse']
export type ReconItem = Schema['ReconItem']

export type InboundOrder = Schema['InboundOrder']
export type InboundOrderDetail = Schema['InboundOrderDetail']
export type InboundOrderCreate = Schema['InboundOrderCreate']
export type ReceiveRequest = Schema['ReceiveRequest']
export type PutawayRequest = Schema['PutawayRequest']

export type OutboundOrder = Schema['OutboundOrder']
export type OutboundOrderDetail = Schema['OutboundOrderDetail']
export type OutboundOrderCreate = Schema['OutboundOrderCreate']
export type PickLine = Schema['PickLine']
export type PickPlanResponse = Schema['PickPlanResponse']
export type PickConfirmRequest = Schema['PickConfirmRequest']
export type ShipRequest = Schema['ShipRequest']

export type OrderLine = Schema['OrderLine']

export type AgentQueryRequest = Schema['AgentQueryRequest']
export type AgentQueryResponse = Schema['AgentQueryResponse']
export type AgentSuggestion = Schema['AgentSuggestion']

// ---------------------------------------------------------------------------
// 2. 前端专属类型（路由 / 权限，非后端契约）
// ---------------------------------------------------------------------------

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
