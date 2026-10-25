// =============================================================================
// MSW Mock Handlers（基于 openapi-msw 类型安全绑定契约 schema）
// -----------------------------------------------------------------------------
// - 用 `createOpenApiHttp<paths>()` 绑定契约类型，path / 参数 / 响应体都由契约推导，
//   字段严格 snake_case，改契约后这里若写错会被 vue-tsc 报出来。
// - 覆盖：认证、主数据、库存、入库作业、出库作业全部接口；Agent 三个接口 501 占位。
// - 错误码模拟：任意接口 URL 加 `?_err=<CODE>` 可触发对应错误（复用 errors.ts 的
//   11 个错误码），方便前端测试弹窗；另含真实业务条件触发的错误（见各 handler 注释）。
// =============================================================================

import { HttpResponse } from 'msw'
import { createOpenApiHttp } from 'openapi-msw'
import type { paths } from '@/api/schema'
import { ERROR_MESSAGES, ERROR_HTTP_STATUS, type ErrorCode } from '@/api/errors'
import {
  skus,
  locations,
  inventoryItems,
  stockTxns,
  reconItems,
  inboundOrders,
  inboundLines,
  outboundOrders,
  outboundLines,
  pickPlan,
} from './data'

const http = createOpenApiHttp<paths>({ baseUrl: 'http://localhost:8000/api/v1' })

/** 通用分页响应体 */
function page<T>(items: T[], p = 1, size = 20) {
  return { items, meta: { total: items.length, page: p, page_size: size } }
}

/** 按单据 id 取明细（mock 数据用「千位段」归组：order 1 → 101/102，order 2 → 201 …） */
function linesOf<T extends { id?: number }>(lines: T[], orderId: number): T[] {
  const lo = orderId * 100
  return lines.filter((l) => (l.id ?? 0) > lo && (l.id ?? 0) < lo + 100)
}

/**
 * 错误响应辅助：返回未绑定 body 泛型的 HttpResponse，
 * 让 openapi-msw 不按状态码做 body 类型推断（错误体 { code, message, detail } 恒定）。
 */
function errorJson(status: number, code: string, message: string, detail?: Record<string, unknown>): Response {
  return HttpResponse.json({ code, message, detail }, { status })
}

/**
 * 错误码模拟：URL 带 `?_err=<CODE>` 时返回对应错误，覆盖 errors.ts 的 11 个错误码。
 * 例：GET /inventory?_err=INVENTORY_INSUFFICIENT → 409 { code, message, detail }
 */
function triggerError(request: Request): Response | null {
  const code = new URL(request.url).searchParams.get('_err')
  if (!code) return null
  const status = ERROR_HTTP_STATUS[code as ErrorCode] ?? 400
  return errorJson(status, code, ERROR_MESSAGES[code as ErrorCode] ?? '未知错误')
}

export const handlers = [
  // ================= 认证 =================
  http.post('/auth/login', async ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    const body = (await request.json()) as { username: string; password: string }
    // 业务错误：密码错误 → UNAUTHORIZED
    if (body.password === 'wrong') return errorJson(401, 'UNAUTHORIZED', '请先登录')
    return HttpResponse.json({ access_token: 'mock-jwt-token', token_type: 'bearer' })
  }),

  http.get('/users/me', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json({ id: 1, username: 'admin', display_name: '系统管理员', role: 'ADMIN' })
  }),

  // ================= 主数据 =================
  http.get('/skus', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json(page(skus))
  }),

  http.post('/skus', async ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    const body = (await request.json()) as { sku_code: string }
    // 业务错误：编码已存在 → SKU_CODE_EXISTS
    if (skus.some((s) => s.sku_code === body.sku_code)) return errorJson(409, 'SKU_CODE_EXISTS', '商品编码已存在')
    const now = new Date().toISOString()
    return HttpResponse.json({ id: 999, status: 1, created_at: now, updated_at: now, ...body }, { status: 201 })
  }),

  http.get('/skus/{id}', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const sku = skus.find((s) => s.id === Number(params.id))
    if (!sku) return errorJson(404, 'NOT_FOUND', '数据不存在')
    return HttpResponse.json(sku)
  }),

  http.put('/skus/{id}', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const sku = skus.find((s) => s.id === Number(params.id))
    if (!sku) return errorJson(404, 'NOT_FOUND', '数据不存在')
    return HttpResponse.json(sku)
  }),

  http.get('/locations', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json({ items: locations })
  }),

  // ================= 库存与流水 =================
  http.get('/inventory', ({ request }) => {
    const e = triggerError(request)
    if (e) return e

    const p = new URL(request.url).searchParams
    let items = [...inventoryItems]

    // sku_code：同时匹配 SKU 编码或条码（PDA 扫条码场景）
    const skuCode = p.get('sku_code')
    if (skuCode) {
      const matchedSkuIds = skus.filter((s) => s.sku_code === skuCode || s.barcode === skuCode).map((s) => s.id)
      items = items.filter((i) => (i.sku_id != null && matchedSkuIds.includes(i.sku_id)) || i.sku_code === skuCode)
    }

    // location_code：精确或前缀匹配（库区如 WH01-A）
    const locationCode = p.get('location_code')
    if (locationCode) items = items.filter((i) => (i.location_code ?? '').startsWith(locationCode))

    // location_type：精确
    const locationType = p.get('location_type')
    if (locationType) items = items.filter((i) => i.location_type === locationType)

    // batch_no：精确
    const batchNo = p.get('batch_no')
    if (batchNo) items = items.filter((i) => i.batch_no === batchNo)

    // expiring_days：N 天内到期（排除哨兵日期 9999-12-31）
    const expiringDays = p.get('expiring_days')
    if (expiringDays) {
      const days = Number(expiringDays)
      if (!Number.isNaN(days)) {
        const deadline = new Date()
        deadline.setDate(deadline.getDate() + days)
        items = items.filter((i) => {
          const exp = i.expiry_date
          return !!exp && !exp.startsWith('9999') && new Date(exp) <= deadline
        })
      }
    }

    // only_available：可用库存 > 0
    if (p.get('only_available') === 'true') items = items.filter((i) => (i.qty_available ?? 0) > 0)

    const pageNo = Number(p.get('page') ?? 1) || 1
    const size = Number(p.get('page_size') ?? 20) || 20
    return HttpResponse.json(page(items, pageNo, size))
  }),

  http.get('/stock-txn', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json(page(stockTxns))
  }),

  http.get('/inventory/recon', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json({ items: reconItems })
  }),

  // ================= 入库作业 =================
  http.get('/inbound-orders', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json(page(inboundOrders))
  }),

  http.post('/inbound-orders', async ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    const body = (await request.json()) as { lines?: unknown[] }
    // 业务错误：缺明细 → VALIDATION_ERROR
    if (!body?.lines?.length) return errorJson(422, 'VALIDATION_ERROR', '参数不合法', { field: 'lines' })
    const now = new Date().toISOString()
    return HttpResponse.json(
      { id: 999, order_no: `IB-${Date.now()}`, status: 'DRAFT', total_expected_qty: 0, total_received_qty: 0, created_at: now, updated_at: now, lines: [] },
      { status: 201 },
    )
  }),

  http.get('/inbound-orders/{id}', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = inboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    return HttpResponse.json({ ...order, lines: linesOf(inboundLines, Number(params.id)) })
  }),

  http.patch('/inbound-orders/{id}/lines/{lineId}', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const line = inboundLines.find((l) => l.id === Number(params.lineId))
    if (!line) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    return HttpResponse.json(line)
  }),

  http.post('/inbound-orders/{id}/receive', async ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = inboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    // 业务错误：非 DRAFT 单收货 → INVALID_STATUS_TRANSITION
    if (order.status !== 'DRAFT') return errorJson(409, 'INVALID_STATUS_TRANSITION', '当前状态不能执行此操作', { status: order.status })
    return HttpResponse.json({ ...order, status: 'RECEIVED', lines: linesOf(inboundLines, Number(params.id)) })
  }),

  http.post('/inbound-orders/{id}/putaway', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = inboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    if (order.status !== 'RECEIVED') return errorJson(409, 'INVALID_STATUS_TRANSITION', '当前状态不能执行此操作', { status: order.status })
    return HttpResponse.json({ ...order, status: 'PUTAWAY', lines: linesOf(inboundLines, Number(params.id)) })
  }),

  http.post('/inbound-orders/{id}/cancel', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = inboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    // 业务错误：DONE 单不可取消 → INVALID_STATUS_TRANSITION
    if (order.status === 'DONE') return errorJson(409, 'INVALID_STATUS_TRANSITION', '当前状态不能执行此操作', { status: order.status })
    return HttpResponse.json({ ...order, status: 'CANCELLED' })
  }),

  // ================= 出库作业 =================
  http.get('/outbound-orders', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json(page(outboundOrders))
  }),

  http.post('/outbound-orders', async ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    const body = (await request.json()) as { lines?: unknown[] }
    if (!body?.lines?.length) return errorJson(422, 'VALIDATION_ERROR', '参数不合法', { field: 'lines' })
    const now = new Date().toISOString()
    return HttpResponse.json(
      { id: 999, order_no: `OB-${Date.now()}`, status: 'DRAFT', priority: 100, total_qty: 0, created_at: now, updated_at: now, lines: [] },
      { status: 201 },
    )
  }),

  http.get('/outbound-orders/{id}', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = outboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    return HttpResponse.json({ ...order, lines: linesOf(outboundLines, Number(params.id)) })
  }),

  http.post('/outbound-orders/{id}/allocate', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = outboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    if (order.status !== 'DRAFT') return errorJson(409, 'INVALID_STATUS_TRANSITION', '当前状态不能执行此操作', { status: order.status })
    // 业务错误：订单 1 需求 300 > 可用库存 → INVENTORY_INSUFFICIENT（detail 带三数，对齐 TC-02）
    if (order.id === 1) {
      return errorJson(409, 'INVENTORY_INSUFFICIENT', '可用库存不足', { sku_code: 'SKU-1001', batch_no: '', required: 300, available: 250, shortfall: 50 })
    }
    return HttpResponse.json({ ...order, status: 'ALLOCATED', lines: linesOf(outboundLines, Number(params.id)) })
  }),

  http.get('/outbound-orders/{id}/pick', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json(pickPlan)
  }),

  http.post('/outbound-orders/{id}/pick', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = outboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    return HttpResponse.json({ ...order, status: 'PICKED', lines: linesOf(outboundLines, Number(params.id)) })
  }),

  http.post('/outbound-orders/{id}/ship', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = outboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    if (order.status !== 'PICKED') return errorJson(409, 'INVALID_STATUS_TRANSITION', '当前状态不能执行此操作', { status: order.status })
    return HttpResponse.json({ ...order, status: 'SHIPPED', shipped_at: new Date().toISOString(), lines: linesOf(outboundLines, Number(params.id)) })
  }),

  http.post('/outbound-orders/{id}/cancel', ({ params, request }) => {
    const e = triggerError(request)
    if (e) return e
    const order = outboundOrders.find((o) => o.id === Number(params.id))
    if (!order) return errorJson(404, 'ORDER_NOT_FOUND', '单据不存在')
    if (order.status === 'SHIPPED') return errorJson(409, 'INVALID_STATUS_TRANSITION', '当前状态不能执行此操作', { status: order.status })
    return HttpResponse.json({ ...order, status: 'CANCELLED' })
  }),

  // ================= AI Agent（P2 占位，契约先定义） =================
  http.post('/agent/queries', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json({ answer: 'Agent 查询占位（P2 实现）', sql_summary: 'SELECT ...', data: [] }, { status: 501 })
  }),
  http.post('/agent/suggestions', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    // 治理红线：Agent 不能直接写库存，只能产生 suggestion → 占位 501
    return HttpResponse.json({ code: 'AGENT_WRITE_FORBIDDEN', message: 'Agent 不能直接写库存', detail: {} }, { status: 501 })
  }),
  http.post('/agent/suggestions/{id}/approve', ({ request }) => {
    const e = triggerError(request)
    if (e) return e
    return HttpResponse.json({}, { status: 501 })
  }),
]
