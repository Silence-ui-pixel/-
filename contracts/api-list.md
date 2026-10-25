# S1-07 接口清单（草稿 v0.1）

> 状态：待评审（D3 与领域模型一起过）
> 产出用途：① S1-08 OpenAPI 契约的直接输入 ② D3 模型评审的对照材料 ③ 发给 B，让他知道要画哪些页面
> 原则：**只覆盖 Sprint 1 最小闭环**（收货 → 上架 → 查询 → 拣货 → 出库），其余全部进「不做清单」。

---

## 一、全局约定（写契约前先冻结这些）

| 项 | 约定 | 说明 |
|---|---|---|
| 前缀 | `/api/v1` | 与骨架 `settings.api_prefix` 一致 |
| 认证 | `Authorization: Bearer <jwt>` | Sprint 1 只做 login 签发 + `GET /users/me`，无刷新 token |
| 分页 | `?page=1&page_size=20`，响应 `{ "items": [...], "total": 123, "page": 1 }` | 最大 page_size=100 |
| 错误格式 | `{ "code": "INVENTORY_INSUFFICIENT", "message": "库存不足", "detail": {...} }` | HTTP 状态码 + 业务错误码双层；错误码枚举进契约 |
| 幂等 | 写操作支持 `Idempotency-Key` 请求头 | **receive / putaway / pick / ship 四个必须有**，PDA 网络差会重试 |
| AI 来源标记 | `X-Agent-Run-Id` 请求头 | Agent 发起的写必须携带；后端落 `stock_txn.source='AGENT'` |
| 状态冲突 | 状态机不允许的流转返回 `409` | 前端据此刷新页面，不做乐观更新 |
| 时间 | 一律 ISO 8601 + UTC | 前端负责本地化 |

**读/写判定的口径**：写 = 会产生 `stock_txn` 或改变单据状态；其余皆读。

---

## 二、接口清单

标注说明：**S1** = 本 Sprint 必须；**P2** = 第二迭代；**暂缓** = 本期不做，契约不定义。

### 2.1 认证（2 条）

| # | 方法 | 路径 | 说明 | 读/写 | 需审批 | 期 |
|---|---|---|---|---|---|---|
| A1 | POST | `/auth/login` | 用户名密码换 JWT（种子账号 admin/sup01/op01） | 写(token) | 否 | S1 |
| A2 | GET | `/users/me` | 当前用户信息与角色（前端控制菜单用） | 读 | 否 | S1 |

> 用户 CRUD **暂缓**：种子数据够用，两个人没有精力做用户管理界面。

### 2.2 主数据（5 条）

| # | 方法 | 路径 | 说明 | 读/写 | 需审批 | 期 |
|---|---|---|---|---|---|---|
| M1 | GET | `/skus` | 商品分页列表（keyword/code/barcode/category 筛选） | 读 | 否 | S1 |
| M2 | GET | `/skus/{id}` | 商品详情 | 读 | 否 | S1 |
| M3 | POST | `/skus` | 新建商品（OPERATOR 及以上） | 写 | 否（主数据双人复核走日志） | S1 |
| M4 | PUT | `/skus/{id}` | 修改商品（**安全库存/补货点改动要落审计**） | 写 | 否 | S1 |
| M5 | GET | `/locations` | 库位列表（zone/type/status 筛选，含 pick_seq） | 读 | 否 | S1 |

> 库位 CRUD **暂缓**：库位是结构化数据，由 `seed.sql` 维护，不做界面。

### 2.3 库存与流水（3 条）

| # | 方法 | 路径 | 说明 | 读/写 | 需审批 | 期 |
|---|---|---|---|---|---|---|
| I1 | GET | `/inventory` | 库存余额查询（sku/location/batch 筛选；`expiring_days=` 效期预警） | 读 | 否 | S1 |
| I2 | GET | `/stock-txn` | 流水查询（sku/order_no/时间范围/source 筛选；**含 AI 来源过滤**） | 读 | 否 | S1 |
| I3 | GET | `/inventory/recon` | 对账视图查询（MANAGER 及以上） | 读 | 否 | S1 |

> **注意**：没有 POST `/inventory`。库存的唯一写入口是下面的作业接口 + `apply_txn`，这是红线在契约层的体现。

### 2.4 入库作业（7 条）

| # | 方法 | 路径 | 说明 | 读/写 | 需审批 | 期 |
|---|---|---|---|---|---|---|
| B1 | GET | `/inbound-orders` | 入库单列表（status/type 筛选） | 读 | 否 | S1 |
| B2 | POST | `/inbound-orders` | 建入库单（头+明细一次提交，状态 DRAFT） | 写 | 否 | S1 |
| B3 | GET | `/inbound-orders/{id}` | 单头+明细+各明细收货进度 | 读 | 否 | S1 |
| B4 | PATCH | `/inbound-orders/{id}/lines/{lineId}` | 改明细数量（仅 DRAFT） | 写 | 否 | S1 |
| B5 | POST | `/inbound-orders/{id}/receive` | 收货：明细按实收数量写入收货暂存位，DRAFT→RECEIVED，走 `apply_txn` | 写 | 否 | S1 |
| B6 | POST | `/inbound-orders/{id}/putaway` | 上架：系统按策略分配目标库位（body 可指定 `line_id` 粒度），走 `apply_txn` | 写 | 否 | S1 |
| B7 | POST | `/inbound-orders/{id}/cancel` | 取消（仅 DRAFT/ARRIVED） | 写 | 否 | S1 |

> 状态机简化说明：schema 里是 7 状态线性推进，Sprint 1 前端只暴露 `DRAFT → RECEIVED → PUTAWAY → DONE` 四个用户可见节点，中间态由后端内部流转。**B5/B6 支持 partial（实收 < 应收）**，部分收货是最小闭环躲不掉的场景。

### 2.5 出库作业（7 条）

| # | 方法 | 路径 | 说明 | 读/写 | 需审批 | 期 |
|---|---|---|---|---|---|---|
| O1 | GET | `/outbound-orders` | 出库单列表（status/priority 筛选） | 读 | 否 | S1 |
| O2 | POST | `/outbound-orders` | 建出库单（头+明细，状态 DRAFT） | 写 | 否 | S1 |
| O3 | GET | `/outbound-orders/{id}` | 单头+明细+分配/拣货进度 | 读 | 否 | S1 |
| O4 | POST | `/outbound-orders/{id}/allocate` | 分配库存：按 FEFO 锁定批次，只动 `allocated_delta`，**失败返回 409 + 可用量明细** | 写 | 否 | S1 |
| O5 | POST | `/outbound-orders/{id}/pick` | 拣货确认：返回拣货路径（按 pick_seq 排序），PDA 逐行确认 | 写 | 否 | S1 |
| O6 | POST | `/outbound-orders/{id}/ship` | 发运：扣减在途 + 落 `stock_txn`，状态 → SHIPPED | 写 | 否 | S1 |
| O7 | POST | `/outbound-orders/{id}/cancel` | 取消（DRAFT/ALLOCATED；ALLOCATED 需回滚分配） | 写 | 否 | S1 |

> **O4 是全系统风险最高的接口**（并发超卖就出在这里），分配逻辑必须进 `apply_txn` 的事务 + 行锁，契约里要把「分配失败的错误结构」定义清楚——B 的前端要做对应的展示。

### 2.6 AI Agent 预留（3 条，契约先定义、S1 只做路由占位）

| # | 方法 | 路径 | 说明 | 读/写 | 需审批 | 期 |
|---|---|---|---|---|---|---|
| G1 | POST | `/agent/queries` | 自然语言查库存（**只读**，返回结构化答案 + 数据来源 SQL 摘要） | 读 | 否 | P2 实现 |
| G2 | POST | `/agent/suggestions` | AI 补货/调拨建议落库（status=PENDING，不直接改库存） | 写 | **是（生成待审批单）** | P2 实现 |
| G3 | POST | `/agent/suggestions/{id}/approve` | 人工审批 → 自动转 B2/O2 正式单据 | 写 | 否（本接口即审批动作） | P2 实现 |

> S1 只在契约里**占位这三个路径 + 空 501 实现**，让 B 的前端和 mock 可以先画 AI 面板骨架。治理规则提前定死：**Agent 永远没有直接写库存的接口**，只能产生 suggestion。

---

## 三、统计与工作量核对

| 分组 | S1 数量 | P2/暂缓 |
|---|---|---|
| 认证 | 2 | — |
| 主数据 | 5 | 库位 CRUD 暂缓 |
| 库存流水 | 3 | — |
| 入库 | 7 | — |
| 出库 | 7 | — |
| Agent | 0（占位） | 3 |
| **合计** | **24 条 S1** | 3 条预留 |

24 条对一个双周 Sprint 的后端是偏重的，但其中 **14 条是纯 CRUD 读**，FastAPI 下每条 30–60 分钟。真正要动脑的是 4 条：**B5/B6（收货上架）、O4（分配）、O6（发运）**，它们全部收敛到 `apply_txn` 一个写入口——这正是当初把 apply_txn 排在 S1-15 的原因。

## 四、给 B 的页面映射（发微信用）

| 页面 | 依赖接口 |
|---|---|
| 登录页 | A1, A2 |
| 商品管理 | M1–M4 |
| 库存查询页（S1-13） | I1（+ I2 看流水） |
| 入库作业台（收货/上架） | B1–B7 |
| 出库作业台（分配/拣货/发运） | O1–O7 |
| 对账/审计（MANAGER） | I3 |
| AI 面板骨架 | G1–G3（501，mock 即可） |

## 五、不做清单（本契约不定义，做了也不接）

- 用户/角色管理 CRUD（种子账号 + 硬编码角色够用）
- 库位管理界面、移库、调拨单（P2 用 inbound/outbound TRANSFER 类型承载）
- 盘点（P3，schema 已预留）
- 波次管理、报表导出、WebSocket 推送、文件上传
- 刷新 token / SSO / 多租户

## 六、待评审的 3 个决策点（D3 会上定）

1. **B5 收货是否落 `stock_txn`？** 方案 A：收货进暂存位即落流水（账实一致更早）；方案 B：上架才落流水（流水更少但收货期间账上无货）。**倾向 A**，暂存位也是库位，账必须实时。
2. **O4 分配粒度**：按单整体分配（简单，但一缺货全卡）vs 按明细逐行分配（推荐，PDA 体验好）。**倾向按明细**，接口语义 `allocate` 天然支持行级重试。
3. **错误码命名**：`DOMAIN_RESOURCE_ACTION`（如 `INVENTORY_INSUFFICIENT`）还是数字段？**倾向大写字符串**，日志和前端可读。

---

*下一步：D3 评审通过后，本清单 1:1 翻译成 `contracts/openapi.yaml`（S1-08）。翻译时每条补齐请求/响应 schema、错误码枚举和两个示例（成功/主要失败）。*
