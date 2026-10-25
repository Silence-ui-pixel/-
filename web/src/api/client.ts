// =============================================================================
// 统一请求入口（基于 openapi-fetch）
// -----------------------------------------------------------------------------
// - `client`：强类型请求客户端，类型来自 src/api/schema.d.ts 的 `paths`（契约唯一真源）。
// - 全局拦截（middleware）：
//     1) onRequest：只注入 `Authorization: Bearer <token>`；
//     2) onResponse：401 → 清凭证并跳登录；其余非 2xx → 统一转 `ApiError`（中文文案）。
//
// ⚠️ 幂等键（Idempotency-Key）**不在这里自动生成**。
//    原因（A 的开发约定）：每次请求新生成 key = 重试时 key 变了 = 等于没有幂等。
//    正确做法：业务层在「用户点击那一刻」调 `makeIdempotencyKey(orderNo, action)` 生成一次，
//    存组件状态；重试时**复用同一个 key**。
// -----------------------------------------------------------------------------
// ⚠️ `X-Agent-Run-Id` 也**不在全局拦截器里塞**：只有 AI 发起的写操作才显式传，
//    否则所有人类操作都会被审计成 source=AGENT。
// =============================================================================

import createClient from 'openapi-fetch'
import type { paths } from './schema'
import { getErrorMessage } from './errors'

/** API 基地址（Mock 关闭时指向真实后端；开启时由 MSW 拦截） */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

/** 与 auth store 保持一致 */
const TOKEN_KEY = 'wms_token'
const USER_KEY = 'wms_user'

/**
 * 统一业务异常：message 已是「可直接弹窗」的中文文案。
 * 抛出时机：非 2xx 响应（后端返回的 code/message 优先，缺失时用 getErrorMessage 兜底）。
 */
export class ApiError extends Error {
  readonly code?: string
  readonly detail?: unknown
  readonly status?: number

  constructor(code: string | undefined, message: string, detail?: unknown, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
    this.status = status
  }
}

/** 强类型请求客户端 */
export const client = createClient<paths>({ baseUrl: BASE_URL })

// ---------------------------------------------------------------------------
// 全局拦截 1：只注入 token（不碰幂等键 / Agent 头）
// ---------------------------------------------------------------------------
client.use({
  async onRequest({ request }) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
})

// ---------------------------------------------------------------------------
// 全局拦截 2：401 → 清凭证跳登录；其余非 2xx → ApiError
// ---------------------------------------------------------------------------
client.use({
  async onResponse({ response }) {
    if (response.ok) return response

    // body 尚未被 openapi-fetch 消费，clone 一份安全读取
    const body = await response.clone().json().catch(() => null)
    const code: string | undefined = body?.code
    const message: string = body?.message ?? getErrorMessage(code ?? '')

    // 401 会话失效：清凭证并跳登录（跳转本身即反馈，不再额外弹 toast）
    // 注意：登录页自身的 401（密码错）不跳转，避免死循环
    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.replace('/login')
      }
    }

    throw new ApiError(code, message, body?.detail, response.status)
  },
})

/**
 * 生成幂等键：业务标识 + 动作 + UUID。
 *
 * **必须**在「用户点击那一刻」调用一次，把结果存进组件状态；重试时复用同一个 key。
 * 每次重试重新生成 = 幂等失效（后端会当成新请求）。
 *
 * @example
 * const key = makeIdempotencyKey(order.order_no, 'RECEIVE')
 * await client.POST('/inbound-orders/{id}/receive', {
 *   params: { path: { id }, header: { 'Idempotency-Key': key } },
 *   body,
 * })
 * // 失败重试时仍是这个 key
 */
export function makeIdempotencyKey(orderNo: string, action: string): string {
  const uuid =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  return `${orderNo}-${action}-${uuid}`
}

/**
 * 把 openapi-fetch 返回的 error 对象转成中文文案（供「不抛异常」场景兜底）。
 * 默认走 ApiError 抛出路径，此函数仅作补充工具。
 */
export function errorToMessage(error: { code?: string; message?: string } | null | undefined): string {
  if (!error) return '操作失败，请稍后重试'
  return error.message || getErrorMessage(error.code || '')
}
