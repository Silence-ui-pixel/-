# 契约变更记录

> 规则见 `CONTRACT-FREEZE.md` 第三节。
> 分类：**允许**（v1.x，不破坏兼容）/ **升版本**（改语义，需要两人确认）/ **禁止**（红线）

---

## v1.0 — 2026-10-25（**冻结**）

首个冻结版本。tag：`contract-v1.0`

### 范围

- 8 张表（`app_user` / `sku` / `location` / `inventory` / `stock_txn` / `inbound_order` / `outbound_order` / `order_line`）
- 23 条路径 / 27 个操作
- 19 个错误码
- `v_inventory_recon` 对账视图 + `stock_txn` 只追加触发器

### 相对冻结前（0.1.0 → 1.0.0）的变更

| # | 变更 | 类型 | 说明 |
|---|---|---|---|
| 1 | 错误响应统一为 `{code, message, detail}` | 升版本 | 原来只有 `DomainError` 走契约格式，`HTTPException` / `RequestValidationError` 返回 `{detail}`。新增两个异常处理器 + `HTTP_STATUS_TO_CODE` 映射表 |
| 2 | `InventoryItem` 新增 `spec` | 允许 | 库存查询页需要显示规格，仅加字段不改语义 |
| 3 | 错误 `detail` 约定为 `{}`（非 `null`） | 允许 | 契约声明 `type: object`，`null` 违反类型 |
| 4 | `contracts/errors.md` 补 7 个通用码 | 允许 | `BAD_REQUEST` / `METHOD_NOT_ALLOWED` / `CONFLICT` / `TOO_MANY_REQUESTS` / `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` / `HTTP_ERROR` |

### v1.0 决议摘要

- D1 库存页 = 10 列全显示 + 窄屏横向滚动
- D2 分配粒度 = 按明细行（**Sprint 2 改造**，当前整单 409）
- D3 部分收货 = 留在 `RECEIVED` 可继续收
- C6 `Idempotency-Key` = 接收但不校验（**Sprint 2 补真幂等**）

完整决议：`A_project/with_B/D3-评审决议.md`

### 冻结时已知欠账（不算违约，已登记）

| 条款 | 现状 | 计划版本 |
|---|---|---|
| `Idempotency-Key` 重放校验 | 未实现，重复提交返回 409 | v1.1 |
| 分配部分成功 | 未实现，整单 409 | v1.1 |
| 跨批次分配 | 未实现 | Sprint 2 |
| 3 条 AI 接口 | 返回 501 占位 | P2 |

---

## 模板（新增变更时复制这一段）

```markdown
## vX.Y — YYYY-MM-DD（状态：待批准 / 已生效）

### 变更 N：<一句话说明>

- **类型**：允许 / 升版本 / 禁止
- **提出方**：
- **原因**：
- **影响范围**：表结构？契约？前端？测试？
- **兼容性**：老调用方会不会挂
- **验证**：跑了哪些测试
```
