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

## v1.1 — 2026-10-25（状态：待批准）

> 由 S1-01 现场口头确认驱动：9 条答案撞出 3 个必须修的行为缺陷。

### 变更 1：分配排除过期批次

- **类型**：升版本（改语义，分配结果可能与 v1.0 不同）
- **提出方**：A（S1-01 现场调研）
- **原因**：现场书面确认「拣货看效期，FEFO 近效期先出」，但 v1.0 实现只按效期升序、不排除已过期批次，导致过期货被发出（实测选中过期 85 天的牛奶）。这是实现与作业规范的正面冲突。
- **影响范围**：`allocation_service.py` 加 `expiry_date >= current_date`；契约 allocate 描述 + 409 说明
- **兼容性**：行为收紧。老调用方不会报错，但「仅有过期批次」时从「分配成功」变为「409 库存不足」
- **验证**：新增 2 测试（跳过过期批次 / 仅过期批次报 409），全量 70 passed

### 变更 2：支持分次收货

- **类型**：升版本（改语义 + 改 `txn_no` 格式）
- **提出方**：A（S1-01 现场调研）
- **原因**：现场确认「一车货会分两次到」，v1.0 实现「一次收货即 RECEIVED」，第二批货到货时被 409 拒绝，三条补救路全堵死。
- **影响范围**：
  - `inbound_orders.py` receive：`txn_no` 加序号（`RECEIPT-{单}-{行}-{seq}`）、`qty_actual` 累加、状态按「是否收满」判断（收满 RECEIVED/DONE，未满 RECEIVING/PARTIAL）
  - 契约 receive 描述 + 状态语义
- **兼容性**：**改 `txn_no` 格式，影响流水追踪**（老 `RECEIPT-{单}-{行}` 变为 `RECEIPT-{单}-{行}-1`）。前端不受影响（响应的 status/qty_actual 字段语义扩展而非破坏）
- **验证**：新增分次收货 + 超收 2 测试，改写原「重复收货 409」测试为「分次累加」，全量 70 passed

### 变更 3：取消/改明细加角色校验

- **类型**：升版本（收紧权限）
- **提出方**：A（S1-01 现场调研）
- **原因**：现场确认「只有主管（MANAGER）能改单/取消」，v1.0 任何登录用户都能（含 VIEWER）。
- **影响范围**：
  - `security.py` 新增 `require_role(*roles)` 依赖工厂
  - `inbound_orders.py` 取消 + 改明细、`outbound_orders.py` 取消，三处加 `Depends(require_role("MANAGER", "ADMIN"))`
  - 契约三处补 403 响应
- **兼容性**：权限收紧。OPERATOR/VIEWER 调用会从「成功」变为「403 FORBIDDEN」，这是预期行为
- **验证**：新增 3 测试（入出库取消 + 改明细的 OPERATOR 拒绝 / MANAGER 通过），全量 70 passed

### 备注

三项改动都改了行为语义，合并登记为 v1.1。若 D3 已冻结（v1.0），则本次属「升版本」，需两人确认后正式生效。详细分析与成本见 `A_project/drafts/S1-01-现场确认结论与系统影响.md`。

---

## v1.2 — 2026-10-26（状态：已生效）

### 变更 1：新增 `GET /users` 用户列表接口

- **类型**：允许（纯新增，不改已有语义）
- **提出方**：A（前端 B 的用户管理页被阻塞）
- **原因**：B 的「用户角色」页面是占位状态，需要一个用户列表接口才能实现。
  原契约只有 `GET /users/me`（当前用户），没有列表。
- **影响范围**：
  - 契约：新增 `/users` 路径 + `UserListItem` / `UserListResponse` 两个 schema
  - 后端：`auth.py` 新增 `list_users`（分页 + keyword/role 过滤）
  - 前端：B 可据此实现用户管理页
- **安全约束（必须守住）**：
  1. **响应绝不含 `password_hash`** —— 用白名单式 `UserListItem` 序列化，不直接 dump ORM
  2. **需 MANAGER/ADMIN** —— OPERATOR/VIEWER 返回 403
- **兼容性**：纯新增，老调用方不受影响
- **验证**：7 个新测试（含「响应不含 password_hash」安全断言）；全量 70 → **77 passed**

---

## v1.3 — 2026-10-26（状态：已生效）

> 由「B 开工前盘点」驱动：两处数据/字段缺口会让前端页面直接做不出来或做出来没法用。

### 变更 1：库位编码统一为业务编码（`location_code = bin_code`）

- **类型**：升版本（改了已有数据的标识值）
- **提出方**：A（盘点 B 的库位管理页时发现）
- **原因**：早期种子数据用拼接编码 `WH01-A-01-01-01`，现场导入数据用业务实际编码 `A0101`。
  两者**是同一个物理库位却存成两行**，后果有两个：
  1. 库位管理页显示 22 条，其中 6 对是同一个物理位，用户无法分辨
  2. `get_functional_location` 按 `id` 取第一个 RECEIVING 位 → 永远命中种子那个虚拟位，
     而现场真实暂存货在 `C0101` → 两处货互不相干，账面上却都「对」
- **影响范围**：
  - `db/seed.sql`：库位块改为现场真实 13 个库位（`A0101`/`B0101`/`C0101`…），编码取 `bin_code`
  - 测试：`conftest.py`、`test_api_batch3.py`（`RECEIVING`/`STAGING`/`STORAGE` 常量）、`test_api_batch4.py`
- **兼容性**：**库位编码值变了**。若有前端代码硬编码 `WH01-A-01-01-01` 会失效（已确认前端无硬编码）
- **验证**：库位数 22 → 13；收货实测落到 `C0101`（现场真实收货区）；对账 14 条 OK；全量 78 passed

### 变更 2：`ReconItem` 新增 `sku_code` / `sku_name` / `location_code`

- **类型**：允许（纯新增字段）
- **提出方**：A
- **原因**：对账项原来只返回 `sku_id` / `location_id`，前端要显示「哪个商品在哪个库位不平」
  必须自己拿两个列表 join，join 不到时无法排查 —— 而排查正是对账页的核心用途
- **影响范围**：`inventory.py` 对账查询 left join `sku` / `location`；契约 `ReconItem` 加 3 字段
- **兼容性**：纯新增，老调用方不受影响
- **验证**：新增 `test_recon_item_includes_codes`；全量 77 → **78 passed**

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
