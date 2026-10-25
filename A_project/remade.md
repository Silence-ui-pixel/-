# A 成员进度看板（实时更新）

> 每次完成一个任务，本文件会立即更新。看这个就知道「现在到哪一步了」。
> 更新时间：**2026-10-25 18:35**

---

## 📍 当前进度一句话

**P1 第 3 批（核心作业：收货/上架/分配/拣货/发运）已完成，全链路端到端跑通，41 测试全绿，对账 100% 一致。** 只剩第 4 批（商品写 + AI 占位）。

---

## ✅ 已完成（按完成顺序）

| # | 任务 | 状态 | 完成时间 | 产出 |
|---|---|---|---|---|
| 1 | 环境预检 | ✅ | 10-24 | `db/schema.sql` 验证通过 |
| 2 | S1-05 仓库骨架 + docker-compose + CI | ✅ | 10-24 | `api/` + `scripts/dev.sh` + CI |
| 3 | S1-07 接口清单 | ✅ | 10-25 | `contracts/api-list.md` |
| 4 | S1-15a apply_txn 四用例断言 | ✅ | 10-25 | `drafts/apply-txn-cases.md` |
| 5 | S1-06 alembic 迁移落地 | ✅ | 10-25 | `api/alembic/versions/0001_baseline.py` |
| 6 | A/B 代码合并到统一仓库 | ✅ | 10-25 | 前端入 `web/` |
| 7 | S1-15b apply_txn 实现 | ✅ | 10-25 | `stock_service.py` + 四用例全绿 |
| 8 | S1-08 OpenAPI 契约 | ✅ | 10-25 | `contracts/openapi.yaml` + `errors.md` |
| 9 | P1 第 1 批：认证+主数据+库存读 | ✅ | 10-25 | 9 条接口，18 测试 |
| 10 | P1 第 2 批：单据 CRUD | ✅ | 10-25 | 9 条接口，31 测试 |
| 11 | **P1 第 3 批：核心作业** | ✅ | 10-25 | 7 条接口，41 测试，全链路对账一致 |

---

## ⏳ A 接下来的工作：P1 剩余批次

| 批次 | 内容 | 状态 |
|---|---|---|
| 第 1 批 ✅ | 认证 / 主数据 / 库存读（9 条接口） | 完成 |
| 第 2 批 ✅ | 单据 CRUD：入库/出库的列表、建单、详情、改明细、取消 | 完成 |
| 第 3 批 ✅ | 核心作业：收货 B5 / 上架 B6 / 分配 O4 / 拣货 O5 / 发运 O6 | 完成 |
| 第 4 批 | 商品写（M3/M4）+ AI 占位（G1/G2/G3 501） | 待开始 |

---

## 🎯 下一步建议（A 的立即行动）

1. **【下一批】P1 第 4 批**：商品增改（M3/M4，写接口需落审计）+ AI 接口 501 占位（G1/G2/G3）
2. 之后 P1 全部结束，进入联调阶段（B 的前端对真接口）

### 第 3 批的作业语义速查（面试/交接时讲得清）

| 动作 | 库存怎么变 | 为什么 |
|---|---|---|
| 收货 RECEIPT | RECEIVING 位 +N | 货到了但没上架，账上必须有，否则「库里有货系统说没有」 |
| 上架 TRANSFER_OUT + PUTAWAY | RECEIVING −N，STORAGE +N | 库存按库位记，一次移库必两条流水 |
| 分配 ALLOCATE | allocated +N（on_hand 不变） | 只锁货不给货，防止两单抢同一批 |
| 拣货 PICK | STORAGE on_hand −N、allocated −N；STAGING +N | 货离开货架但还在仓库，记到发货暂存位才账实一致 |
| 发运 SHIP | STAGING −N | 货真正离仓，账上才消失 |
| 取消 DEALLOCATE | allocated −N | 不放回就是永久性库存泄漏 |

### 关键技术红线（贯穿 P1）

1. 每个接口对着 `contracts/openapi.yaml` 实现，契约是唯一真源
2. 写接口全部调用 `stock_service.apply_txn`，不直接改 inventory
3. 先写测试再实现，核心作业接口必须有测试
4. 幂等头 `Idempotency-Key`、AI 头 `X-Agent-Run-Id` 已在第 3 批落地

---

## ⚠️ 已知限制（Sprint 1 明确不做，不是 bug）

1. **不支持跨批次分配**：一条出库明细只能绑一个批次/库位。单批次不足直接 409 并提示拆单。
   跨批次需要独立的 allocation 明细表，属 Sprint 2。
2. **不支持多次部分收货**：一次收货完成整单。多次收货会破坏 txn_no 的天然幂等。
3. **批次商品未强制效期**：只强制批次号，效期缺省用哨兵。冷链商品的效期校验属 P2。

---

## 👥 等 B / 需两人同场

| 任务 | 类型 | 说明 |
|---|---|---|
| B 同步代码 + S1-11/S1-12 | B 进行中 | 契约已交付，B 正在生成 TS 类型 + 搭 mock |
| S1-01 现场跟单调研 | 两人同场（D1） | **A 可提前准备**：列调研问题清单 |
| S1-02 一页纸范围声明 | 两人同场（D2） | **A 可提前起草**「不做什么」半页 |
| S1-03 痛点+指标 | 两人同场（D2） | **A 可提前想** 3 条痛点 |
| **S1-04 模型评审冻结** | 两人同场（D3） | 分歧已文档对齐，只剩「库存查询页默认列」 |
| S1-09 契约评审冻结 | 两人同场（D8） | — |
| S1-16 复盘 | 两人同场（D10） | — |

---

## 📁 关键文件速查

| 文件 | 说明 |
|---|---|
| `../contracts/openapi.yaml` | OpenAPI 契约（唯一真源） |
| `../contracts/errors.md` | 错误码 + 中文提示 |
| `../api/app/services/stock_service.py` | apply_txn 库存写入口 |
| `../api/app/services/allocation_service.py` | FEFO 分配算法 |
| `../api/app/services/location_service.py` | 暂存位查找 + 上架目标位策略 |
| `../api/app/core/errors.py` | DomainError 体系（含 HTTP 状态码） |
| `../api/app/api/v1/` | 已实现路由（health/auth/skus/inventory/inbound/outbound） |
| `notes/daily-log.md` | 每日工作日志 |

