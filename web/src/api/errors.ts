// =============================================================================
// 错误码 → 中文提示 映射
// 来源：contracts/errors.md（与 contracts/openapi.yaml 配套，仅 A 可改）
// 用途：页面弹窗 / Toast 直接取中文文案，不硬编码、不猜。
//
// 约定（见 errors.md）：
//   - HTTP 状态码决定前端「重试 / 刷新」策略；业务错误码 code 决定展示文案。
//   - 判断逻辑用 code；展示文案优先用 message，复杂场景用 detail 拼装。
// =============================================================================

/** 业务错误码枚举（来自 contracts/errors.md） */
export type ErrorCode =
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'SKU_CODE_EXISTS'
  | 'INVENTORY_INSUFFICIENT'
  | 'INVENTORY_DIM_MISMATCH'
  | 'INVALID_STATUS_TRANSITION'
  | 'ORDER_NOT_FOUND'
  | 'AGENT_WRITE_FORBIDDEN'

/** 错误码 → 中文提示（可直接 import 使用） */
export const ERROR_MESSAGES: Record<ErrorCode, string> = {
  UNAUTHORIZED: '请先登录',
  FORBIDDEN: '没有权限执行此操作',
  NOT_FOUND: '数据不存在',
  VALIDATION_ERROR: '参数不合法',
  SKU_CODE_EXISTS: '商品编码已存在',
  INVENTORY_INSUFFICIENT: '可用库存不足',
  INVENTORY_DIM_MISMATCH: '库存维度不匹配',
  INVALID_STATUS_TRANSITION: '当前状态不能执行此操作',
  ORDER_NOT_FOUND: '单据不存在',
  AGENT_WRITE_FORBIDDEN: 'Agent 不能直接写库存',
}

/** 错误码 → HTTP 状态码（供前端判断重试 / 刷新策略） */
export const ERROR_HTTP_STATUS: Record<ErrorCode, number> = {
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  VALIDATION_ERROR: 422,
  SKU_CODE_EXISTS: 409,
  INVENTORY_INSUFFICIENT: 409,
  INVENTORY_DIM_MISMATCH: 409,
  INVALID_STATUS_TRANSITION: 409,
  ORDER_NOT_FOUND: 404,
  AGENT_WRITE_FORBIDDEN: 403,
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
