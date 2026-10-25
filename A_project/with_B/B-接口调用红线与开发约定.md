# B 前端开发约定 · 接口调用红线

> 作者：A · 日期 2026-10-25 20:25
> 用途：**写代码时对照这一份就够**，不用每次翻 openapi.yaml
> 配套：`contracts/errors.md`（错误码表）、`contracts/openapi.yaml`（字段结构）

---

## 〇、先看这一张表（收藏这一段）

六个写接口要带什么头：

| 接口 | 方法 | `Idempotency-Key` | `X-Agent-Run-Id` | 谁在用 |
|---|---|---|---|---|
| `/inbound-orders/{id}/receive` 收货 | POST | **必带** | AI 发起时带 | PDA |
| `/inbound-orders/{id}/putaway` 上架 | POST | **必带** | 同上 | PDA |
| `/outbound-orders/{id}/allocate` 分配 | POST | **必带** | 同上 | PC |
| `/outbound-orders/{id}/pick` 拣货 | POST | **必带** | 同上 | PDA |
| `/outbound-orders/{id}/ship` 发运 | POST | **必带** | 同上 | PDA |
| `/outbound-orders/{id}/cancel` 取消 | POST | 建议带 | — | PC |

**除 login 外所有接口**：`Authorization: Bearer <jwt>`
**所有写操作**：`Content-Type: application/json`

> 建单（`POST /inbound-orders`、`POST /outbound-orders`）目前不需要幂等键，重复建单会生成两张单——**这是刻意的**（业务上确实可能开两张），前端用按钮禁用防抖即可。

---

## 一、为什么需要这些头（三层防御，各管一件事）

很多人以为幂等头是"可选的礼貌"，不是。这三个东西管的是**三个不同的故障**：

| 层 | 机制 | 挡住什么故障 |
|---|---|---|
| 1 | `Authorization` | 谁在操作 |
| 2 | `Idempotency-Key` | **同一次操作被发了两次**（弱网重试、用户手抖双击、PDA 扫码连击） |
| 3 | `X-Agent-Run-Id` | **这次操作是谁（人还是 AI）发起的**，出问题能追到具体 Agent 会话 |

PDA 在仓库里信号差是常态：请求发出去了、服务器处理完了、响应在路上丢了。客户端以为失败，自动重试——**如果没有幂等机制，货会被收两遍**。

---

## 二、`Idempotency-Key`：怎么生成、怎么重试

### 2.1 生成规则

**核心要求：同一次用户操作的所有重试，必须用同一个 key。**

```ts
// ✅ 推荐：业务标识 + 动作 + 随机后缀，在「用户点击那一刻」生成一次
function makeIdempotencyKey(orderNo: string, action: string): string {
  // crypto.randomUUID() 现代浏览器/PDA WebView 都支持
  return `${orderNo}-${action}-${crypto.randomUUID()}`
}

// 用法：点击时生成，存在局部变量/组件状态里，重试时复用
const key = makeIdempotencyKey(order.order_no, 'RECEIVE')
await receive(order.id, body, key)
// 失败重试时，还是传这个 key —— 千万别重新生成
```

```ts
// ❌ 错：每次请求都生成新 key
async function receive(orderId, body) {
  return api.post(`/inbound-orders/${orderId}/receive`, body, {
    headers: { 'Idempotency-Key': crypto.randomUUID() },  // 重试时是新 key，等于没有幂等
  })
}

// ❌ 错：用时间戳拼，重试时秒数变了就变新 key
'Idempotency-Key': `receive-${Date.now()}`
```

### 2.2 后端当前的真实行为（重要，请按这个写，别按想象写）

我必须如实告诉你现在的实现状态：

| 项 | 现状 |
|---|---|
| 契约要求 | `required: true`（见 openapi.yaml 第 63 行） |
| 后端接收 | ✅ 已接收（5 个接口都声明了） |
| **重放校验** | ❌ **尚未实现**（Sprint 2 补） |
| 重复提交实际返回 | **409 `INVALID_STATUS_TRANSITION`**，不是静默成功 |

**实测证据**（我刚跑的，你可以自己复现）：

```
第 1 次收货 → 200，单据变 RECEIVED
第 2 次（同 key，同 body）→ 409
{"code":"INVALID_STATUS_TRANSITION",
 "message":"当前状态（RECEIVED）不能执行「收货」",
 "detail":{"order_no":"IN-20261025-500B11","current_status":"RECEIVED",
           "action":"收货","allowed_statuses":["ARRIVED","DRAFT","RECEIVING"]}}
```

### 2.3 好消息：库存绝不会重复扣

即使重复提交，库存也不会错乱，因为有两道**业务层**保护：

1. **状态机**：单据已经是 `RECEIVED`，第二次收货直接被 409 拦下，一行代码都没执行
2. **`txn_no` 天然唯一**：`RECEIPT-{order_id}-{line_id}`，就算绕过状态机，`apply_txn` 也会识别为重复流水

所以现在的风险**不是数据错乱，而是 UI 骗人**：用户看到"收货失败"，实际上一秒前已经成功了。

### 2.4 因此前端必须做这两件事

**① 请求期间禁用按钮 + 全局锁**

```ts
const submitting = ref(false)
async function onReceive() {
  if (submitting.value) return       // 双击/连击直接忽略
  submitting.value = true
  try {
    await receive(order.id, body, key)
  } finally {
    submitting.value = false
  }
}
```

**② 写操作失败时，先查状态再决定要不要报错** —— 这条比幂等键更重要

```ts
async function receiveWithRecovery(orderId: number, body: ReceiveBody, key: string) {
  try {
    return await api.post(`/inbound-orders/${orderId}/receive`, body, {
      headers: { 'Idempotency-Key': key },
    })
  } catch (e: any) {
    // 409 且是状态机冲突 —— 极可能是"上次其实成功了，响应丢了"
    if (e.response?.status === 409 &&
        e.response?.data?.code === 'INVALID_STATUS_TRANSITION') {
      const latest = await api.get(`/inbound-orders/${orderId}`)

      // 目标状态已达成 → 视为成功，别再报错吓用户
      if (latest.data.status === 'RECEIVED') {
        ElMessage.success('收货成功')
        return latest.data        // 直接返回最新单据，UI 照常刷新
      }
    }
    throw e                        // 其它错误正常抛出
  }
}
```

这个模式叫「**失败后先对账**」，比盲目重试安全得多。适用于全部 5 个写接口（把 `RECEIVED` 换成各自的目标状态即可）：

| 接口 | 目标状态 |
|---|---|
| receive | `RECEIVED` |
| putaway | `PUTAWAY`（全部上架后） |
| allocate | `ALLOCATED` |
| pick | `PICKED` |
| ship | `SHIPPED` |

### 2.5 Sprint 2 会发生什么变化（提前告知）

我会补上真正的重放校验。届时行为变成：

```
同 key 重复提交 → 直接返回第一次的成功响应（200），不报 409
```

**你的代码不需要改** —— 因为上面 2.4 的兜底逻辑在两种行为下都正确。这也是我建议你现在就写兜底的原因。

---

## 三、`X-Agent-Run-Id`：现在用不上，但要知道

### 3.1 它是真生效的（和 Idempotency-Key 不同）

```python
# api/app/api/v1/inbound_orders.py
def _source_of(agent_run_id: str | None) -> str:
    return "AGENT" if agent_run_id else "WEB"
```

这个头会写进 `stock_txn` 两个字段：

| 字段 | 值 |
|---|---|
| `source` | 有头 → `AGENT`；无头 → `WEB` |
| `agent_run_id` | 头的原值，用于追溯具体 Agent 会话 |

### 3.2 前端要不要带？

**Sprint 1：不用带。** 你所有操作都是人在 PC/PDA 上点的，`source=WEB` 就是正确答案。

**Sprint 2/3 才会用到**：AI Agent 替你执行写操作时，必须带这个头，否则审计上分不清"人干的"还是"AI 干的"。

### 3.3 但你现在要做一件事：别在封装里乱塞

如果你在 axios 拦截器里统一加这个头，会导致**所有人类操作都被记成 AGENT**，审计数据全废。

```ts
// ❌ 千万别这样
api.interceptors.request.use((config) => {
  config.headers['X-Agent-Run-Id'] = someGlobalValue   // 全站都变成 AGENT 来源
  return config
})

// ✅ 只在 AI 触发的调用里显式传
await api.post(url, body, { headers: { 'X-Agent-Run-Id': aiRunId } })
```

---

## 四、错误处理规范

### 4.1 所有错误的形状（已统一，不用再兼容 `detail` 字符串）

```ts
interface ApiError {
  code: string       // 永远存在，用它做分流
  message: string    // 永远存在，中文，直接展示给用户
  detail: object     // 永远存在且是对象（无附加信息时是 {}，不是 null）
}
```

**可以删掉你之前写的 `message ?? detail字符串 ?? 错误码映射` 兜底**——现在 `message` 一定存在。

### 4.2 按 `code` 分流的处理表

| HTTP | code | 前端该做什么 |
|---|---|---|
| 401 | `UNAUTHORIZED` | 清本地 token → 跳登录页（**别弹 toast**，跳转本身就是反馈） |
| 403 | `FORBIDDEN` | 提示「没有权限」，并隐藏/禁用对应入口 |
| 404 | `NOT_FOUND` | 提示「数据不存在」，列表页刷新 |
| 409 | `INVENTORY_INSUFFICIENT` | **弹缺货明细**：`detail.sku_code / available / shortfall`，提示「请拆分该明细」 |
| 409 | `INVALID_STATUS_TRANSITION` | 提示「状态已变化，请刷新」，并自动刷新当前单据（**这也是重复提交的信号**，见 2.4） |
| 422 | `VALIDATION_ERROR` | 有 `detail.errors` 时**标红对应输入框**；无 errors 时直接展示 `message` |
| 501 | `NOT_IMPLEMENTED` | 提示「功能开发中」，不要当报错处理 |
| 5xx | `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` | 提示「服务异常，请稍后重试」，可上报 |

### 4.3 错误码常量（直接复制，别手写字符串）

```ts
// web/src/api/errorCodes.ts —— 与 contracts/errors.md 保持一致
export const ErrorCode = {
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVENTORY_INSUFFICIENT: 'INVENTORY_INSUFFICIENT',
  INVENTORY_DIM_MISMATCH: 'INVENTORY_DIM_MISMATCH',
  INVALID_STATUS_TRANSITION: 'INVALID_STATUS_TRANSITION',
  ORDER_NOT_FOUND: 'ORDER_NOT_FOUND',
  SKU_CODE_EXISTS: 'SKU_CODE_EXISTS',
  SKU_BATCH_FLAG_CONFLICT: 'SKU_BATCH_FLAG_CONFLICT',
  AGENT_WRITE_FORBIDDEN: 'AGENT_WRITE_FORBIDDEN',
  NOT_IMPLEMENTED: 'NOT_IMPLEMENTED',
} as const

export type ErrorCode = typeof ErrorCode[keyof typeof ErrorCode]
```

### 4.4 422 的字段定位怎么用

```ts
// detail.errors 结构（真实返回，我验证过）
// { errors: [{ loc: ["body","lines"], msg: "Field required", type: "missing" }] }

function pickFieldErrors(err: ApiError): Record<string, string> {
  const out: Record<string, string> = {}
  const errors = (err.detail as any)?.errors ?? []
  for (const e of errors) {
    // loc = ["body","lines",0,"qty_actual"] → 取末级字段名
    const field = e.loc?.[e.loc.length - 1]
    if (typeof field === 'string') out[field] = e.msg
  }
  return out
}
```

> ⚠️ `msg` 是**英文**（Pydantic 原文，如 `Field required`），给开发看，**不要直接展示给用户**。展示用顶层 `message`。

---

## 五、三个必须避开的坑

### 坑 1：前端自己算 `qty_available`

```ts
// ❌ 绝对不要
const available = item.qty_on_hand - item.qty_allocated
```

它是 PG 生成列，后端算好给你。前端再算一次，就会出现两个真相，对不上时无法判断谁对。

**正确**：直接用 `item.qty_available`，且**永远不提交它**。

### 坑 2：`stock_txn` 想改就改

流水表是只追加的，数据库触发器会拦 UPDATE / DELETE。前端任何"撤销/修改历史"的想法都要放弃，只能**再写一条反向流水**（这也是为什么取消单据要调 `cancel` 接口，而不是改数据）。

### 坑 3：用 200 判断成功，不看 body

分配接口失败是 409（有 body），但**批量操作可能出现部分成功**（Sprint 2）。养成读 body 的习惯：

```ts
const res = await api.post(...)
// 别只看 res.status，关键业务结果在 body 里
```

---

## 六、提交前自检清单

写这些页面时，逐条对：

**收货 / 上架 / 拣货 / 发运页**
- [ ] 请求带 `Idempotency-Key`，且**重试时复用同一个 key**
- [ ] 按钮在请求期间禁用（含 PDA 扫码连击防抖）
- [ ] 409 时先 GET 单据状态再决定报错（2.4 的兜底）
- [ ] 收货必须校验「批次管理商品填了批次号」（否则后端 422）

**库存查询页**
- [ ] 用 `qty_available` 显示可用量，不自己算
- [ ] 支持 `location_type` 筛选（默认可排除 `RECEIVING` 暂存位）
- [ ] 规格列用 `spec`，批次列用 `batch_no`

**全局**
- [ ] 401 统一跳登录，不在拦截器里弹 toast
- [ ] 错误码用 `ErrorCode` 常量，不手写字符串
- [ ] `X-Agent-Run-Id` 不在全局拦截器里塞
- [ ] 分页 `page_size` 不超过 100

---

## 七、有疑问时怎么办

| 疑问类型 | 看哪里 |
|---|---|
| 字段结构、必填与否 | `contracts/openapi.yaml` |
| 错误码含义、触发场景 | `contracts/errors.md` |
| 某个状态能不能做某个操作 | `A_project/drafts/api-list.md` 的状态机图 |
| 库存为什么是这个数 | `A_project/drafts/apply-txn-cases.md` |
| 都对不上 | 直接问我，别猜 |

**最重要的一条**：契约和代码不一致时，**以契约为准**，然后告诉我——是我要改代码去符合契约，不是你改代码去迁就现状。
