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
| `BAD_REQUEST` | 400 | 请求不合法 | 参数语义错误但未触发字段校验 |
| `METHOD_NOT_ALLOWED` | 405 | 请求方法不允许 | 用错 HTTP 方法（如 DELETE 一个只读接口） |
| `CONFLICT` | 409 | 操作冲突 | 未带业务错误码的通用冲突 |
| `TOO_MANY_REQUESTS` | 429 | 请求过于频繁 | 触发限流 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 未捕获异常（前端应提示重试并上报） |
| `SERVICE_UNAVAILABLE` | 503 | 服务暂不可用 | 依赖不可用（如数据库连不上） |
| `HTTP_ERROR` | 其他 | 请求失败 | 上表未收录状态码的兜底 |

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
- `detail` **永远是 object**（没有附加信息时是 `{}`，不是 `null`）—— 前端可以直接点取字段，不用判空
- `detail` 是结构化附加信息，**不同错误码的 detail 字段不同**（见各接口的 409 说明）
- 前端判断逻辑用 `code`，展示文案优先用 `message`，复杂场景用 `detail` 拼装

---

## 实现保证：所有异常都是这个格式

后端在 `api/app/main.py` 注册了三个异常处理器，**没有任何一条错误路径能绕过**：

| 异常来源 | 处理器 | 举例 |
|---|---|---|
| `DomainError`（业务） | `handle_domain_error` | 库存不足、状态机不允许 |
| `HTTPException`（框架/路由） | `handle_http_exception` | 401 未登录、403 权限、404 不存在、405 方法错、503 依赖挂了 |
| `RequestValidationError`（Pydantic） | `handle_validation_error` | 请求体缺字段、类型不对 |

状态码 → 错误码的映射表在 `api/app/core/errors.py` 的 `HTTP_STATUS_TO_CODE`，
**改码表必须同步改本文件**。

### 422 的 `detail` 结构（前端标红具体输入框用）

```json
{
  "code": "VALIDATION_ERROR",
  "message": "参数不合法",
  "detail": {
    "errors": [
      { "loc": ["body", "lines"], "msg": "Field required", "type": "missing" }
    ]
  }
}
```

- `loc`：字段路径数组，`["body","lines"]` 表示请求体里的 `lines` 字段
- `msg`：英文原文（开发排查用，不要直接展示给用户）
- `type`：错误类别（`missing` / `greater_than` / `string_type` 等）
- 给用户看的永远是顶层 `message`

> 注意区分：**路由里手工抛的 422**（如「实收数量不能为负数」）走 `HTTPException`
> 分支，`message` 就是那句中文；**Pydantic 校验失败**走 `VALIDATION_ERROR` 分支，
> `message` 固定「参数不合法」，具体原因在 `detail.errors`。
