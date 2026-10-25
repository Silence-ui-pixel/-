// =============================================================================
// 统一请求入口（基于 openapi-fetch）
// -----------------------------------------------------------------------------
// - `client`：强类型请求客户端，类型来自 src/api/schema.d.ts 的 `paths`（契约唯一真源）。
//   所有接口方法（GET/POST/PUT/PATCH）都由 openapi-fetch 按契约自动推导，字段严格 snake_case。
// - 全局拦截（middleware）：
//     1) 请求头注入 `Authorization: Bearer <token>`；
//     2) 写操作（POST/PUT/PATCH）自动注入 `Idempotency-Key` 幂等头（PDA 弱网重试必需，
//        业务层可显式传更精确的幂等键，如 `SO-001-PICK`）；
//     3) 非 2xx 响应统一转成 `ApiError`（message 已是中文文案），调用层 catch 后可直接弹窗。
// =============================================================================

import createClient from 'openapi-fetch'
import type { paths } from './schema'
import { getErrorMessage } from './errors'

/** API 基地址（Mock 关闭时指向真实后端；开启时由 MSW 拦截） */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

/** 与 auth store 保持一致 */
const TOKEN_KEY = 'wms_token'

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
// 全局拦截 1：注入 token + 幂等头
// ---------------------------------------------------------------------------
client.use({
  async onRequest({ request }) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }

    // 写操作注入幂等头（PDA 弱网重试时同一次业务提交用同一个 key，避免重复扣减）
    const method = request.method.toUpperCase()
    if (method === 'POST' || method === 'PUT' || method === 'PATCH') {
      if (!request.headers.has('Idempotency-Key')) {
        request.headers.set('Idempotency-Key', genIdempotencyKey())
      }
    }
    return request
  },
})

// ---------------------------------------------------------------------------
// 全局拦截 2：非 2xx → 统一转 ApiError（中文文案）
// ---------------------------------------------------------------------------
client.use({
  async onResponse({ response }) {
    if (response.ok) return response

    // 此时 body 尚未被 openapi-fetch 消费，clone 一份安全读取，不破坏后续解析
    const body = await response
      .clone()
      .json()
      .catch(() => null)

    const code: string | undefined = body?.code
    // 兼容两种错误体：
    //   1) 契约格式 { code, message, detail }（mock 与目标实现）
    //   2) FastAPI 默认 { detail: "中文描述" }（当前后端部分接口的实际返回）
    const rawDetail = body?.detail
    const message: string =
      body?.message ?? (typeof rawDetail === 'string' ? rawDetail : undefined) ?? getErrorMessage(code ?? '')
    throw new ApiError(code, message, body?.detail, response.status)
  },
})

/** 生成默认幂等键（业务层可显式覆盖，传更可读的 `业务单号-动作`） */
function genIdempotencyKey(): string {
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * 把 openapi-fetch 返回的 error 对象转成中文文案（供「不抛异常」场景兜底）。
 * 默认走 ApiError 抛出路径，此函数仅作补充工具。
 */
export function errorToMessage(error: { code?: string; message?: string } | null | undefined): string {
  if (!error) return '操作失败，请稍后重试'
  return error.message || getErrorMessage(error.code || '')
}
