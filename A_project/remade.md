# A 成员进度看板（实时更新）

> 每次完成一个任务，本文件会立即更新。看这个就知道「现在到哪一步了」。
> 更新时间：**2026-10-25 18:15**

---

## 📍 当前进度一句话

**P1 第 2 批（单据 CRUD）已实现并验证通过（31 测试全绿）。** A 的可独立技术任务持续推进中，下一步是第 3 批核心作业（走 apply_txn）。

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
| 9 | P1 第 1 批：认证+主数据+库存读 | ✅ | 10-25 | 9 条接口落地，18 测试全绿 |
| 10 | **P1 第 2 批：单据 CRUD** | ✅ | 10-25 | 入库 5 + 出库 4 接口落地，31 测试全绿 |

---

## ⏳ A 接下来的工作：P1 剩余批次

| 批次 | 内容 | 状态 |
|---|---|---|
| 第 1 批 ✅ | 认证 / 主数据 / 库存读（9 条接口） | 完成 |
| 第 2 批 ✅ | 单据 CRUD：入库/出库的列表、建单、详情、改明细、取消 | 完成 |
| 第 3 批 | 核心作业：收货 B5 / 上架 B6 / 分配 O4 / 拣货 O5 / 发运 O6（走 apply_txn） | 待开始 |
| 第 4 批 | 商品写（M3/M4）+ AI 占位（G1/G2/G3 501） | 待开始 |

---

## 🎯 下一步建议（A 的立即行动）

1. **【下一批】P1 第 3 批（核心）**：收货 B5 / 上架 B6 / 分配 O4 / 拣货 O5 / 发运 O6，全部走 apply_txn
   - 这是全系统最关键的一批：串起 apply_txn + 真实业务流 + 幂等头 + AI 治理头
   - 先写测试（延续先红后绿），尤其 O4 分配的 409 结构和幂等
2. **第 4 批**：商品写（M3/M4）+ AI 占位（G1/G2/G3 501）

### 关键技术红线（贯穿 P1）

1. 每个接口对着 `contracts/openapi.yaml` 实现，契约是唯一真源
2. 写接口（B5/B6/O4/O5/O6）全部调用 `stock_service.apply_txn`，不直接改 inventory
3. 先写测试再实现，核心作业接口必须有测试
4. 幂等头 `Idempotency-Key`、AI 头 `X-Agent-Run-Id` 在第 3 批落实

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
| `../contracts/openapi.yaml` | OpenAPI 契约（唯一真源，P1 照着实现） |
| `../contracts/errors.md` | 错误码 + 中文提示 |
| `../contracts/api-list.md` | 27 条接口清单 |
| `../api/app/services/stock_service.py` | apply_txn 库存写入口 |
| `../api/app/db/models.py` | ORM 模型（8 张表） |
| `../api/app/api/v1/` | 已实现路由（health/auth/skus/inventory/inbound_orders/outbound_orders） |
| `drafts/apply-txn-cases.md` | apply_txn 四用例断言 |
| `notes/daily-log.md` | 每日工作日志 |

---

> ⚠️ 网络提示：git push 此前因代理 502 失败，本地已 commit 多笔（`399dd1f`、`4778477` 等），网络恢复后统一补 push。
