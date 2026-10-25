// =============================================================================
// 业务错误码常量（与 contracts/errors.md 严格一致）
// -----------------------------------------------------------------------------
// 用法：判断逻辑一律用 `ErrorCode.XXX`，不要手写字符串（拼错不报错、排查很痛）。
// 改码表必须同步改 contracts/errors.md 与后端 api/app/core/errors.py。
// =============================================================================

export const ErrorCode = {
  // ---- 通用 ----
  UNAUTHORIZED: 'UNAUTHORIZED', // 401 请先登录
  FORBIDDEN: 'FORBIDDEN', // 403 没有权限
  NOT_FOUND: 'NOT_FOUND', // 404 数据不存在
  VALIDATION_ERROR: 'VALIDATION_ERROR', // 422 参数不合法
  BAD_REQUEST: 'BAD_REQUEST', // 400 请求不合法
  METHOD_NOT_ALLOWED: 'METHOD_NOT_ALLOWED', // 405 方法不允许
  CONFLICT: 'CONFLICT', // 409 通用冲突
  TOO_MANY_REQUESTS: 'TOO_MANY_REQUESTS', // 429 限流
  INTERNAL_ERROR: 'INTERNAL_ERROR', // 500 服务器内部错误
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE', // 503 服务暂不可用
  HTTP_ERROR: 'HTTP_ERROR', // 其他状态码兜底

  // ---- 商品 ----
  SKU_CODE_EXISTS: 'SKU_CODE_EXISTS', // 409 商品编码已存在
  SKU_BATCH_FLAG_CONFLICT: 'SKU_BATCH_FLAG_CONFLICT', // 409 有库存不能改批次管理

  // ---- 库存 ----
  INVENTORY_INSUFFICIENT: 'INVENTORY_INSUFFICIENT', // 409 可用库存不足
  INVENTORY_DIM_MISMATCH: 'INVENTORY_DIM_MISMATCH', // 409 库存维度不匹配

  // ---- 状态机（入库/出库通用）----
  INVALID_STATUS_TRANSITION: 'INVALID_STATUS_TRANSITION', // 409 状态不允许
  ORDER_NOT_FOUND: 'ORDER_NOT_FOUND', // 404 单据不存在

  // ---- AI Agent（P2）----
  AGENT_WRITE_FORBIDDEN: 'AGENT_WRITE_FORBIDDEN', // 403 Agent 不能直接写库存
  NOT_IMPLEMENTED: 'NOT_IMPLEMENTED', // 501 功能待实现
} as const

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]
