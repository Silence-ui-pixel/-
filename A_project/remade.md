# A 成员进度看板（实时更新）

> 每次完成一个任务，本文件会立即更新。看这个就知道「现在到哪一步了」。
> 更新时间：**2026-10-25 21:10**

---

## 📍 当前进度一句话

🎉 **P1 完成 + 首轮联调已修完 B 反馈的问题（64 测试全绿）。** 错误响应格式已全量对齐契约，`InventoryItem` 补了 `spec`；现在只差 B 确认两件事（`detail` 用 `{}`、库存页默认 6 列），签完 D3 即可冻结契约。

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
| 9 | P1 第 1 批：认证+主数据+库存读 | ✅ | 10-25 | 9 条接口 |
| 10 | P1 第 2 批：单据 CRUD | ✅ | 10-25 | 9 条接口 |
| 11 | P1 第 3 批：核心作业 | ✅ | 10-25 | 7 条接口，全链路对账一致 |
| 12 | **P1 第 4 批：商品增改 + AI 占位** | ✅ | 10-25 | 2 写接口 + 3 个 501 占位 |
| 13 | 代码推送到 GitHub `origin/main` | ✅ | 10-25 | `7cfa27e` 已上远程，本地/远程完全一致 |
| 14 | 核查 B 的推送是否到达远程 | ⚠️ 待 B 确认 | 10-25 | 远程 main 最新仍为 `3305133`，未见 B 新提交 |
| 15 | **修 B 反馈：错误响应格式统一** | ✅ | 10-25 | 两个异常处理器 + `HTTP_STATUS_TO_CODE`，401/403/404/422 全部转契约结构 |
| 16 | **`InventoryItem` 补 `spec` 字段** | ✅ | 10-25 | 库存页可显示规格；契约/schema/路由三处同步 |
| 17 | 首轮联调问题全部闭环 | ✅ | 10-25 | 64 测试全绿；真实 HTTP 6 场景逐个验证 |
| 18 | **S1-01/02/03 材料准备** | ✅ 材料已备 | 10-25 | 调研包 + 范围声明 + 指标矩阵（3 份，见下） |
| 19 | **D3 模型评审 + 契约冻结** | ✅ **已冻结 v1.0** | 10-25 | 决议 + 冻结声明 + CHANGELOG + tag `contract-v1.0` |
| 20 | **P2 启动准备：AI 治理设计** | ✅ 设计就绪 | 10-25 | `drafts/P2-AI治理设计与启动准备.md` + `agent.py` 注释升级为 5 条红线 |

---

## 🔧 本轮修复详情（B 联调反馈驱动）

**B 的报告**：`A_project/with_B/B-联调反馈-错误响应格式.md`
**我的回复**：`A_project/with_B/A-回复-错误格式已修复.md`（可直接发给他）

### 问题本质

只有 `DomainError`（业务错误）走了契约格式，FastAPI 内置的 3 类异常仍是默认 `{detail}`：

| 异常来源 | 修复前 | 修复后 |
|---|---|---|
| `DomainError` | ✅ 契约格式 | 不变 |
| `HTTPException` | ❌ `{detail}` | ✅ `{code, message, detail}` |
| `RequestValidationError` | ❌ `{detail: [...]}` | ✅ `VALIDATION_ERROR` + `detail.errors` |

### 关键决策：`detail` 用 `{}` 不是 `null`

B 建议写 `detail: None`，**我没照做** —— `contracts/openapi.yaml` 里 `detail` 声明为 `type: object` 且无 `nullable`，返回 `null` 会违反契约，前端若做 schema 校验会直接炸。统一给 `{}`，前端可以永远 `err.detail ?? {}`。

### 改动文件

| 文件 | 改动 |
|---|---|
| `api/app/main.py` | 加 `StarletteHTTPException` + `RequestValidationError` 两个处理器；**保留原异常 headers**（401 的 `WWW-Authenticate` 不能丢） |
| `api/app/core/errors.py` | 加 `HTTP_STATUS_TO_CODE` 映射表（11 个状态码）+ `clean_validation_errors()`（洗掉 Pydantic 里不可序列化的 `ctx.error` / `bytes input`） |
| `api/app/schemas/__init__.py` | `InventoryItem` 加 `spec: str \| None` |
| `api/app/api/v1/inventory.py` | 查询带出 `sku.spec` |
| `contracts/openapi.yaml` | `InventoryItem.spec`（`nullable: true`） |
| `contracts/errors.md` | 补 7 个通用码 + 422 detail 结构 + 三处理器对照表 |
| `scripts/dev.sh` | `up` 后检测 `app_user` 表，缺表提示跑 `db-init` |
| `api/tests/test_error_format.py` | **新增 8 个测试**守护错误格式 |

### 两个隐蔽坑（值得记住）

1. **Pydantic 的 `ctx` 可能塞着 `ValueError` 实例、`input` 可能是 `bytes`** → 直接 `JSONResponse` 会抛 "not JSON serializable" 变成 500，把「参数错了」误导成「服务器崩了」。`clean_validation_errors()` 统一转成原始类型。
2. **`detail` 类型必须与契约一致** → 这是「契约唯一真源」原则的实战检验：B 的建议在语义上合理，但在契约上非法，不能照抄。

### 验证结果

真实 HTTP 逐场景抓包（非仅单测）：

| # | 场景 | 实际返回 |
|---|---|---|
| ① | 登录密码错 | `{"code":"UNAUTHORIZED","message":"用户名或密码错误","detail":{}}` |
| ② | 未带 token | `{"code":"UNAUTHORIZED","message":"缺少认证信息","detail":{}}` |
| ③ | OPERATOR 查对账 | `{"code":"FORBIDDEN","message":"需要仓管主管及以上权限","detail":{}}` |
| ④ | 入库单 999999 | `{"code":"NOT_FOUND","message":"入库单不存在","detail":{}}` |
| ⑤ | 建单缺 lines | `{"code":"VALIDATION_ERROR","detail":{"errors":[{"loc":["body","lines"],...}]}}` |
| ⑥ | 库存不足（对照） | `{"code":"INVENTORY_INSUFFICIENT","detail":{...完整 8 字段}}` |

**测试统计**：55 → **64 个全绿**（+8 错误格式 +1 spec 字段）。
**契约校验**：OpenAPI 3.1 `validate()` 通过，23 条路径。

### 等 B 回的两件事

1. `detail` 用 `{}` 还是 `null`（我坚持 `{}`，除非他有强需求）
2. 库存查询页默认 6 列是否确认（`sku_code / sku_name / spec / location_code / batch_no+expiry_date / qty_available`）→ 确认后 **D3 契约冻结**

---

## ⚠️ B 同步状态核查（2026-10-25 18:45）

**核查结论：远程没有 B 的新提交，我这边已是最新，无需 pull。**

三重交叉验证（都指向同一结果）：

| 验证方式 | 结果 |
|---|---|
| `git fetch` + `rev-list --left-right --count` | 本地/远程 `0 0`，零差异 |
| `git fetch "+refs/heads/*"` 全引用抓取 | 远程只有 `main` 一个分支，无其他分支 |
| GitHub commits 页面抓取 | 最新 commit = `3305133`（A 18:41 推的看板更新） |

**远程 main 提交时间线**：

| 时间 | 作者 | 提交 | 说明 |
|---|---|---|---|
| 18:41 | HeYao669 | `3305133` | A：看板更新 |
| 18:35 | HeYao0 | `7cfa27e` | A：P1 第 4 批收尾 |
| 18:29 | HeYao0 | `8c0e987` | A：合并 B 的前端进度 |
| **18:24** | **siuhdiuwqhd（B）** | **`6f0dea5`** | **B 最后一次成功推送** |

**B 的 `6f0dea5` 内容本地已完整落地**（17 个文件，+4514 行），磁盘核对无缺失：
`web/src/api/schema.d.ts`(1681行)、`client.ts`(96)、`mocks/handlers.ts`(331)、`views/inventory/query/index.vue`、`views/pda/scan.vue`、`package.json` 等全部存在，工作区干净。

### 最可能的原因：B 也撞上了同一个网络问题

本机实测 **GitHub HTTPS 443 直连不通**，只有本地代理可用。B 大概率同样情况——`git push` 报错但被忽略，或误以为"推了"。

### 让 B 执行这 4 条自查（可直接转发）

```bash
git log origin/main -1 --oneline     # 他认知的远程最新是什么
git status -sb                       # 是否显示 ahead N（N 就是他没推上去的提交数）
git push origin main                 # 看真实报错
git ls-remote origin HEAD            # 远程真实 HEAD 的 sha
```

- 若 `git status` 显示 `ahead N` → **确实没推上去**，按下面修
- 若报 `Failed to connect to github.com port 443` → 就是 443 被封，改走 SSH（见下）

### 给 B 的稳定通道建议：改用 SSH（22 端口实测是通的）

```bash
ssh-keygen -t ed25519 -C "B@canku"        # 已有密钥可跳过
cat ~/.ssh/id_ed25519.pub                  # 复制为 GitHub → Settings → SSH keys
ssh -T git@github.com                      # 出现 "Hi <用户名>!" 即成功
git remote set-url origin git@github.com:Silence-ui-pixel/-.git
 git push origin main
```

> 22 端口不需要代理，绕开 443 封锁，比折腾代理更省事。

### 若 B 其实推到了别处

让他确认：① 是否推到自己的 **fork** ② 是否推到**另一个仓库** ③ 是否在网页上建了 **PR 但目标分支写错**。任一情况把地址/分支名发我，我这边直接 fetch 合并。

---

## 🔌 网络通道备注（下次 push 可复用）

- GitHub **HTTPS 443 直连不通**（`gitclone.com` 镜像也无法 push），唯一可用通道是 **本地代理 `127.0.0.1:7897`**。
- 已在仓库级固化：`git config http.proxy http://127.0.0.1:7897`，直接 `git push` / `git pull` 即可。
- `git config --global url....insteadOf` 的镜像改写**已移除**（若恢复会把地址改回 `gitclone.com` 导致推送失败）。
- 若某天 7897 代理关了，先验证 `curl -x http://127.0.0.1:7897 https://github.com/` 是否 200。

---

## ✅ P1 已全部完成

| 批次 | 内容 | 状态 |
|---|---|---|
| 第 1 批 ✅ | 认证 / 主数据 / 库存读（9 条接口） | 完成 |
| 第 2 批 ✅ | 单据 CRUD：入库/出库的列表、建单、详情、改明细、取消 | 完成 |
| 第 3 批 ✅ | 核心作业：收货 / 上架 / 分配 / 拣货 / 发运 | 完成 |
| 第 4 批 ✅ | 商品增改 + AI 接口 501 占位 | 完成 |

**接口覆盖**：契约 27 条 → 实现 25 条（另 2 条 AI 接口按设计返回 501）→ 55 个测试。

---

## 🎯 下一步（按优先级）

1. **D3 模型评审 + 契约冻结** —— ✅ **已完成，契约冻结 v1.0**（2026-10-25）

   | 项 | 内容 |
   |---|---|
   | 决议 | `A_project/with_B/D3-评审决议.md`（9 项议题全部有结论，0 项待定） |
   | 冻结声明 | `contracts/CONTRACT-FREEZE.md`（范围 / 变更规则 / 真源优先级 / 验证方式） |
   | 变更记录 | `contracts/CHANGELOG.md`（v1.0 首条） |
   | tag | `contract-v1.0` |
   | 版本 | `openapi.yaml` 0.1.0 → **1.0.0**（FastAPI 同步） |

   **决议摘要**：D1 库存页 10 列 + 窄屏横滚 / D2 分配按明细行（Sprint 2）/ D3 部分收货留 RECEIVED / C6 幂等欠账认可过渡方案
   **验证**：64 测试全绿 + 契约 `validate()` 通过（23 路径）+ `db-check` 账实一致

2. **与 B 联调**：B 的 MSW Mock 已就绪，可切真实 API 对拍
   - 📄 **先把这份发给 B**：`with_B/B-接口调用红线与开发约定.md`
     （6 个写接口的头要求速查 + 幂等键真实行为 + 错误分流表 + 3 个必避坑 + 自检清单 + 可直接复制的 TS 代码）
   - 错误码文案直接用 `contracts/errors.md`
   - 错误格式已按 B 的反馈统一（见上方「本轮修复详情」）
   - ⚠️ 关键提醒：`Idempotency-Key` 目前只接收不校验，重复提交返回 409（详见「已知限制」第 6 条）
3. **S1-01/02/03 材料准备** —— ✅ **已完成，三份文档在 `drafts/` 下**
   | 文档 | 用途 | 关键内容 |
   |---|---|---|
   | `drafts/S1-01-现场跟单调研包.md` | 带去现场的工具 | 9 个待验证设计假设 + 3 张记录表（改单次数/隐形字段/作业时序） |
   | `drafts/S1-02-范围声明-不做什么.md` | 两人签字 | 12 条「不做」+ 换出机制 + 待调研后翻转的 4 条 |
   | `drafts/S1-03-指标可行性矩阵.md` | 决定报什么指标 | 9 个指标判定：5 个能算、2 个改口径、2 个必须砍 |

   **三份材料里最值得记住的 3 个结论**：
   - **库存准确率算不出来**：8 张表没有盘点表，`v_inventory_recon` 校验的是「账 vs 流水」，不是「账 vs 实物」，拿它冒充准确率会在汇报时被问穿
   - **缺货率也算不出来**：409 只返回前端不落库；且 `SHORT` 不在 `ck_line_status` 约束里，`PARTIAL` 已被拣货占用，补它要动迁移 → Sprint 1 砍掉
   - **`inventory` 表没有 `created_at`**，只有 `updated_at`（写呆滞率 SQL 时会踩）

   **指标 SQL 全部实跑验证过**，抓出 2 个错误（`percentile_cont` 需 `::numeric`；`inventory` 无 `created_at`）。
4. **P2 启动准备** —— ✅ **设计就绪**：`drafts/P2-AI治理设计与启动准备.md`

   **核心主张**：约束写在注释里等于没有约束。所以 5 条红线每条都配有「强制点」——
   能指出哪一行代码 / 哪一条数据库权限真的拦得住。

   | 红线 | 强制点 |
   |---|---|
   | AI 永不写库存 | `apply_txn` 唯一入口 + AI 专用只读 DB 角色（物理隔离） |
   | 产出只能是建议 | 只能写 `agent_suggestion`，状态默认 PENDING，无建单代码路径 |
   | 审批必须人触发 | 带 `X-Agent-Run-Id` 调 approve → 403 `AGENT_WRITE_FORBIDDEN`；`approved_by` not null |
   | 每次调用留痕 | `agent_run` 表 + `stock_txn.agent_run_id`（**Sprint 1 已预留该字段**） |
   | SQL 必须过白名单 | sqlglot 解析（单条 SELECT + 表白名单 + 强制 LIMIT）→ 只读角色兜底 |

   **新增 2 张表的 DDL 已写好**（`agent_run` / `agent_suggestion`），P2 开工可直接迁移。
   **9 条攻击用例**已列为验收清单（含 `delete`、CTE 写、多语句、`pg_sleep`、`copy`）。
   **工作量**：A 约 6 人天，B 约 2 人天。

   ⚠️ **开工前必须定 3 件事**（不写代码但要先定，否则返工）：
   ① 用哪个模型 API ② AI 允许查哪些表 ③ 审批人是 MANAGER 还是 ADMIN

### 第 3 批的作业语义速查（面试/交接时讲得清）

| 动作 | 库存怎么变 | 为什么 |
|---|---|---|
| 收货 RECEIPT | RECEIVING 位 +N | 货到了但没上架，账上必须有 |
| 上架 TRANSFER_OUT + PUTAWAY | RECEIVING −N，STORAGE +N | 库存按库位记，一次移库必两条流水 |
| 分配 ALLOCATE | allocated +N（on_hand 不变） | 只锁货不给货，防止两单抢同一批 |
| 拣货 PICK | STORAGE −N、allocated −应拣；STAGING +实拣 | 货离开货架但还在仓库 |
| 发运 SHIP | STAGING −N | 货真正离仓 |
| 取消 DEALLOCATE | allocated −N | 不放回就是永久性库存泄漏 |

---

## ⚠️ 已知限制（Sprint 1 明确不做，不是 bug）

1. **不支持跨批次分配**：一条出库明细只能绑一个批次/库位。不足直接 409 并提示拆单。跨批次需 allocation 明细表，属 Sprint 2。
2. **不支持多次部分收货**：一次收货完成整单（否则 txn_no 失去天然幂等）。
3. **批次商品未强制效期**：只强制批次号，效期缺省用哨兵 9999-12-30。
4. **商品主数据无审计表**：写操作只落结构化日志，正式审计表属 Sprint 2（`skus.py` 注释已写明）。
5. **商品修改不开放 sku_code / barcode**：契约未给，编码变更会影响历史单据指向。
6. **`Idempotency-Key` 已声明但未做重放校验** ⚠️ 契约要求必带（openapi 第 63 行 `required: true`），5 个写接口都接收了该头，但**没有任何代码使用它**。实测重复提交返回 409 而非幂等成功。
   - **数据安全没问题**：状态机 + `txn_no` 唯一双重保护，库存绝不会重复扣减
   - **问题是 UI 骗人**：弱网重试时用户看到「失败」，实际上一次已成功
   - **当前对策**：前端「失败后先 GET 单据状态再决定报错」（已写进 `with_B/B-接口调用红线与开发约定.md` 第 2.4 节）
   - **正解**：Sprint 2 加幂等记录表（key → 响应快照），同 key 重复直接返回首次响应。届时要改契约语义，属 v1.1

---

## 👥 等 B / 需两人同场

| 任务 | 类型 | 说明 |
|---|---|---|
| **D3 模型评审冻结** | 两人同场 | **材料已备齐**：`with_B/D3-评审材料包.md` + `notes/D3-主持手册.md` + `with_B/D3-评审决议-模板.md`，75 分钟可完成 |
| 与 B 联调 | 两人协作 | B 的 Mock 就绪，可切真接口 |
| S1-01 现场跟单调研 | 两人同场 | **A 可提前准备**：列调研问题清单 |
| S1-02 一页纸范围声明 | 两人同场 | **A 可提前起草**「不做什么」半页 |
| S1-03 痛点+指标 | 两人同场 | **A 可提前想** 3 条痛点 |
| S1-09 契约评审冻结 | 两人同场（D8） | — |
| S1-16 复盘 | 两人同场（D10） | — |

---

## 📁 关键文件速查

| 文件 | 说明 |
|---|---|
| `../contracts/openapi.yaml` | OpenAPI 契约（唯一真源，27 条接口） |
| `../contracts/errors.md` | 错误码 + 中文提示 |
| `../api/app/services/stock_service.py` | apply_txn 库存写入口 |
| `../api/app/services/allocation_service.py` | FEFO 分配算法 |
| `../api/app/services/location_service.py` | 暂存位查找 + 上架目标位策略 |
| `../api/app/core/errors.py` | DomainError 体系（含 HTTP 状态码） |
| `../api/app/api/v1/` | 7 个路由模块（health/auth/skus/inventory/inbound/outbound/agent） |
| `notes/daily-log.md` | 每日工作日志 |


