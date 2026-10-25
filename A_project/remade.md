# A 成员进度看板（实时更新）

> 每次完成一个任务，本文件会立即更新。看这个就知道「现在到哪一步了」。
> 更新时间：**2026-10-25 17:45**

---

## 📍 当前进度一句话

**A 的 6 个独立技术任务全部完成，契约已冻结。** B 正在同步代码并推进他的 S1-11/S1-12。A 的下一步是**进入 P1：把契约里的 24 条接口真正实现出来**（这是纯 A 的技术活，不用等 B）。

---

## ✅ 已完成（按完成顺序）

| # | 任务 | 状态 | 完成时间 | 产出 |
|---|---|---|---|---|
| 1 | 环境预检（真实 PG 跑通建库） | ✅ 完成 | 10-24 | `db/schema.sql` 验证通过 |
| 2 | S1-05 仓库骨架 + docker-compose + CI | ✅ 完成 | 10-24 | `api/` + `scripts/dev.sh` + CI |
| 3 | S1-07 接口清单 | ✅ 完成 | 10-25 | `contracts/api-list.md`：27 条接口 |
| 4 | S1-15a apply_txn 四用例断言 | ✅ 完成 | 10-25 | `drafts/apply-txn-cases.md` |
| 5 | S1-06 alembic 迁移落地 | ✅ 完成 | 10-25 | `api/alembic/versions/0001_baseline.py` |
| 6 | A/B 代码合并到统一仓库 | ✅ 完成 | 10-25 | 前端入 `web/`，push 到 GitHub |
| 7 | S1-15b apply_txn 实现 | ✅ 完成 | 10-25 | `stock_service.py` + 四用例全绿 |
| 8 | S1-08 OpenAPI 契约 | ✅ 完成 | 10-25 | `contracts/openapi.yaml` + `errors.md`，规范校验通过 |

## 🔄 进行中

- （无）

## ⏳ A 接下来的工作：进入 P1（接口实现）

> 契约已冻结，B 在同步 + 做他的 S1-11/S1-12。A 现在**不需要等任何人**，直接开始把 24 条接口从契约落到 FastAPI。

### P1 接口实现的建议顺序（由易到难，4 批）

**第 1 批：纯读 + 主数据（最快，先热身）**
- 商品：M1 `GET /skus`、M2 `GET /skus/{id}`、M5 `GET /locations`
- 库存读：I1 `GET /inventory`、I2 `GET /stock-txn`、I3 `GET /inventory/recon`
- 认证：A1 `POST /auth/login`、A2 `GET /users/me`

**第 2 批：单据 CRUD（不碰库存）**
- 入库：B1 列表、B2 建单、B3 详情、B4 改明细、B7 取消
- 出库：O1 列表、O2 建单、O3 详情、O7 取消

**第 3 批：核心作业（走 apply_txn，最关键）**
- B5 收货（RECEIPT）、B6 上架（PUTAWAY）
- O4 分配（ALLOCATE）、O5 拣货（PICK）、O6 发运（SHIP）

**第 4 批：商品写 + AI 占位**
- M3/M4 商品增改（写，落审计）
- G1/G2/G3 AI 接口（501 占位，P2 实现）

### 关键技术提醒

1. **每个接口都要对着 `contracts/openapi.yaml` 实现**，不能凭记忆——契约是唯一真源
2. **写接口（B5/B6/O4/O5/O6）全部调用 `stock_service.apply_txn`**，不直接改 inventory（红线）
3. **先写测试再写实现**（延续 apply_txn 的先红后绿），至少核心作业接口要有测试
4. 幂等头 `Idempotency-Key`、AI 头 `X-Agent-Run-Id` 的处理要在第 3 批落实

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
| `../api/app/db/models.py` | ORM 模型 |
| `drafts/apply-txn-cases.md` | apply_txn 四用例断言 |
| `notes/daily-log.md` | 每日工作日志 |

---

## 🎯 下一步建议（A 的立即行动）

1. **【现在就能做】进入 P1 第 1 批**：实现主数据 + 库存读接口（M1/M2/M5、I1/I2/I3、A1/A2），这批最快、最没风险
2. **第 2 批**：单据 CRUD（入库/出库的列表/建单/详情/取消）
3. **第 3 批（核心）**：收货 B5 / 上架 B6 / 分配 O4 / 拣货 O5 / 发运 O6，全部走 apply_txn
4. **穿插**：D3 前把 S1-01/02/03 的材料先准备好（调研问题、范围声明草稿、3 条痛点）

**给 B 的通知已发，B 正在同步。A 不用等，直接开干 P1 第 1 批。**
