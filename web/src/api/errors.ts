// =============================================================================
// 错误码 → 中文提示 / HTTP 状态映射
// 来源：contracts/errors.md（仅 A 可改；改码表须同步 errorCodes.ts）
// 用途：页面弹窗 / Toast 直接取中文文案，不硬编码、不猜。
//
// 约定（见 errors.md）：
//   - HTTP 状态码决定前端「重试 / 刷新」策略；业务错误码 code 决定展示文案。
//   - 判断逻辑用 code；展示文案优先用后端 message，缺失时用本表兜底。
//   - detail 永远是 object（无附加信息时为 {}），可直接点取字段。
// =============================================================================

import { ErrorCode } from './errorCodes'

export { ErrorCode } from './errorCodes'

/** 错误码 → 中文提示（后端 message 缺失时的兜底文案） */
export const ERROR_MESSAGES: Record<ErrorCode, string> = {
  // 通用
  UNAUTHORIZED: '请先登录',
  FORBIDDEN: '没有权限执行此操作',
  NOT_FOUND: '数据不存在',
  VALIDATION_ERROR: '参数不合法',
  BAD_REQUEST: '请求不合法',
  METHOD_NOT_ALLOWED: '请求方法不允许',
  CONFLICT: '操作冲突',
  TOO_MANY_REQUESTS: '请求过于频繁，请稍后再试',
  INTERNAL_ERROR: '服务器内部错误，请稍后重试',
  SERVICE_UNAVAILABLE: '服务暂不可用，请稍后重试',
  HTTP_ERROR: '请求失败',
  // 商品
  SKU_CODE_EXISTS: '商品编码已存在',
  SKU_BATCH_FLAG_CONFLICT: '该商品已有库存，不能改为批次管理',
  // 库存
  INVENTORY_INSUFFICIENT: '可用库存不足',
  INVENTORY_DIM_MISMATCH: '库存维度不匹配',
  // 状态机
  INVALID_STATUS_TRANSITION: '当前状态不能执行此操作',
  ORDER_NOT_FOUND: '单据不存在',
  // AI Agent
  AGENT_WRITE_FORBIDDEN: 'Agent 不能直接写库存',
  NOT_IMPLEMENTED: '该功能将在 P2 阶段实现',
}

/** 错误码 → HTTP 状态码（供前端判断重试 / 刷新策略；0 表示「其他」） */
export const ERROR_HTTP_STATUS: Record<ErrorCode, number> = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  VALIDATION_ERROR: 422,
  BAD_REQUEST: 400,
  METHOD_NOT_ALLOWED: 405,
  CONFLICT: 409,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
  HTTP_ERROR: 0,
  SKU_CODE_EXISTS: 409,
  SKU_BATCH_FLAG_CONFLICT: 409,
  INVENTORY_INSUFFICIENT: 409,
  INVENTORY_DIM_MISMATCH: 409,
  INVALID_STATUS_TRANSITION: 409,
  ORDER_NOT_FOUND: 404,
  AGENT_WRITE_FORBIDDEN: 403,
  NOT_IMPLEMENTED: 501,
}

/**
 * 取错误码对应的中文提示；未知错误码回退为通用文案。
 * @param code 后端返回的业务错误码
 */
export function getErrorMessage(code: string): string {
  if (code in ERROR_MESSAGES) {
    return ERROR_MESSAGES[code as ErrorCode]
  }
  return '操作失败，请稍后重试'
}
