# 错误码枚举（与 openapi.yaml 配套）

> 每个错误码配一句中文提示，B 直接拿去显示，不要让他猜。
> 命名规范：大写蛇形 `DOMAIN_RESOURCE_ACTION`。
> HTTP 状态码 + 业务错误码双层：HTTP 决定前端重试/刷新策略，错误码决定展示文案。

## 通用

| 错误码 | HTTP | 中文提示 | 触发场景 |
|---|---|---|---|
| `UNAUTHORIZED` | 401 | 请先登录 | 未带 token 或 token 失效 |
| `FORBIDDEN` | 403 | 没有权限执行此操作 | 角色权限不足（如对账需 MANAGER） |
| `NOT_FOUND` | 404 | 数据不存在 | 查询的 id 不存在 |
| `VALIDATION_ERROR` | 422 | 参数不合法 | 请求体校验失败 |

## 商品

| 错误码 | HTTP | 中文提示 | 触发场景 |
|---|---|---|---|
| `SKU_CODE_EXISTS` | 409 | 商品编码已存在 | 新建商品时 sku_code 重复 |
| `SKU_BATCH_FLAG_CONFLICT` | 409 | 该商品已有库存，不能改为批次管理 | 有库存的商品改 is_batch_managed=false→true（历史库存无批次号会断链） |

## 库存

| 错误码 | HTTP | 中文提示 | 触发场景 |
|---|---|---|---|
| `INVENTORY_INSUFFICIENT` | 409 | 可用库存不足 | 出库/分配时可用量 < 需求 |
| `INVENTORY_DIM_MISMATCH` | 409 | 库存维度不匹配 | 批次/效期等维度与预期不符 |

## 状态机（入库/出库通用）

| 错误码 | HTTP | 中文提示 | 触发场景 |
|---|---|---|---|
| `INVALID_STATUS_TRANSITION` | 409 | 当前状态不能执行此操作 | 状态机不允许的流转（如 DONE 后再收货） |
| `ORDER_NOT_FOUND` | 404 | 单据不存在 | 单据 id 不存在 |

## AI Agent（P2）

| 错误码 | HTTP | 中文提示 | 触发场景 |
|---|---|---|---|
| `AGENT_WRITE_FORBIDDEN` | 403 | Agent 不能直接写库存 | Agent 尝试直接写库存（治理红线） |
| `NOT_IMPLEMENTED` | 501 | 该功能将在 P2 阶段实现 | G1/G2/G3 接口在 Sprint 1 只占位 |

> **为什么 AI 接口用 501 而不是 404**：501 明确表示「接口存在，只是还没实现」。
> 前端可以据此显示「功能开发中」，而 404 会和「路径写错了」混在一起，排查时浪费时间。

---

## 错误响应统一格式

```json
{
  "code": "INVENTORY_INSUFFICIENT",
  "message": "可用库存不足",
  "detail": {
    "sku_code": "SKU-1001",
    "batch_no": "B20261001",
    "required": 40,
    "available": 30,
    "shortfall": 10
  }
}
```

**约定**：
- `code` + `message` 永远存在
- `detail` 是结构化附加信息，**不同错误码的 detail 字段不同**（见各接口的 409 说明）
- 前端判断逻辑用 `code`，展示文案优先用 `message`，复杂场景用 `detail` 拼装
