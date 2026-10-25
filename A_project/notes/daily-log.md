# 工作日志 · A 成员

> 每天三行就够：**今天推进了什么、卡在哪、明天第一步**。
> 不要写成周报，写给自己看的。

---

## 2026-10-24 (D0 · 开工前)

**推进**
- 建了 A 的工作区，把 12 张任务卡按「能独自推进 / 必须两人 / 等 B 的信息」重新分了类
- 在真实 PG 引擎上跑通 `db/schema.sql`，20 项断言全过

**发现**
- 种子数据不可重复导入 → 加 `on conflict do nothing`
- DDL 和种子混在一个文件 → 拆成 `schema.sql` + `seed.sql`

**卡点（已解决）**
- Docker Desktop 没启动 → 已启动
- 补跑 `verify-schema.sh` 失败 → 不是端口被占用，是 **Windows 保留端口段**（55348–56247）撞上了 `-p 55432`。脚本全程走 `docker exec`，根本不需要发布端口，已改为默认不映射 + `PUBLISH=1` 自动避让

**验证结论**
- 真实 PG 16 全部通过，与离线版一致

**明天第一步**
- 写 `drafts/api-list.md`（8 张表 → 资源 → 动作，标注读写与是否需审批）
- 然后 `drafts/apply-txn-cases.md`（四个用例断言）

---

## 2026-10-24 (D0 · S1-05 完成)

**推进**
- `git init` + 完整骨架：`api/`（FastAPI + async SQLAlchemy）、`scripts/dev.sh`、`docker-compose.yml`、`Makefile`、CI
- 一条命令 `bash scripts/dev.sh up` 起 db + api，88 秒（含首次构建）
- `db-init` 建库播种成功，对账 1 行 OK；`/health` `/health/db` `/docs` 全通
- pytest 3 passed，ruff All checks passed
- 干净克隆验证：clone 到临时目录后 `docker compose build` 成功
- 两个 commit，工作区干净

**踩坑**
- `/sql/schema.sql` 被 Git Bash(MSYS) 改写成 Windows 路径 → 改用 stdin 重定向
- `dev.sh` 函数定义写在 `case` 之后，bash 还没定义就用了 → 移到前面
- ruff B008 对 FastAPI `Depends()` 误报 → `extend-immutable-calls` 精确豁免
- 脚本在 git 里是 100644 → `update-index --chmod=+x` 改 100755

**明天第一步**
- S1-07 接口清单（同时是 D3 评审输入 + S1-08 前置）
- 给 B 发两条消息：骨架能跑了 / 先画哪 3 个页面

---

## 2026-10-25 (D1 · S1-07 完成)

**推进**
- `drafts/api-list.md` v0.1：8 张表 → 6 组资源 → **27 条接口**（S1 必须 24 条 + AI 预留 3 条 501 占位）
- 全局约定先于路径定死：错误码双层结构、写操作 Idempotency-Key（PDA 重试必需）、`X-Agent-Run-Id` 治理标记
- 明确 **没有 POST /inventory** —— 库存唯一写入口是作业接口 + apply_txn，红线在契约层落地
- 给 B 的 7 个页面已映射好接口依赖，可直接发微信
- 3 个待评审决策点已备好倾向方案：收货即落流水（A）/ 按明细分配（行级）/ 错误码用大写字符串

**发现**
- 状态机 7 状态对前端太碎，契约只暴露 DRAFT→RECEIVED→PUTAWAY→DONE 四个用户可见节点，中间态后端内部流转
- O4 allocate 是风险最高接口（并发超卖点），错误结构要带可用量明细给前端展示

**明天第一步**
- D3 模型评审（带上 api-list 一起过，6 项都在场）
- S1-15a：apply_txn 四用例断言（`drafts/apply-txn-cases.md`）

---

## 2026-10-25 (D1 · S1-15a 完成)

**推进**
- `drafts/apply-txn-cases.md`：四个用例断言（TC-01 正常入库 / TC-02 库存不足 / TC-03 并发扣减 / TC-04 幂等），每个用例 4–5 条断言 + 前置数据 + 期望
- 明确 apply_txn 五步（锁行→校验→写余额→写流水→提交），快照在锁内现算、**不信任入参**
- 关键语义钉死：可用量 = `qty_on_hand - qty_allocated`，TC-02 专门用「已分配一部分」的维度验证；幂等靠 txn_no 锁内先查；并发要双连接+栅栏，不能顺序跑

**发现**
- `tasks-A.csv` 被外部程序（疑似 Excel）独占锁定，S1-15a 状态字段写不进，待解锁后补写

**明天第一步**
- 补 CSV 状态（解锁后）
- D3 模型评审（api-list + apply-txn-cases 一起过）
- 之后 S1-06 alembic 迁移（依赖 S1-05 已完成）

---

## 2026-10-25 (D1 · S1-06 完成)

**推进**
- 接入 alembic，初始迁移 `api/alembic/versions/0001_baseline.py` 等价于 schema.sql 全部 DDL
- `dev.sh` 新增 `db-migrate`，`db-init` 改为「迁移 + 播种」，`db-reset` 走新流程
- 迁移在真实 PG 16 上跑通：8 表 + alembic_version、8 触发器、33 索引、生成列、对账视图全就位
- 关键约束复验：只追加保护 / 负库存拦截 / 快照自洽 三个 CHECK 全生效

**踩坑（三个，都值得记）**
1. **`op.create_trigger` 不存在** —— alembic 1.20 都没有这个 API（长期提案未合并）。改用 `op.execute("create trigger ...")` 原生语句，8 个触发器全换掉
2. **缺 `psycopg` 同步驱动** —— env.py 把 asyncpg URL 转成 `postgresql+psycopg://`，但没装 psycopg。加 `psycopg[binary]` 依赖
3. **PyPI 官方源 read timed out** —— 国内直连 files.pythonhosted.org 不稳定。Dockerfile 的 pip 加清华镜像 + `--timeout 120 --retries 5`

**明天第一步**
- D3 模型评审（api-list + apply-txn-cases + alembic 基线一起过）
- 之后 S1-15b apply_txn 实现（四用例断言已备好，先红后绿）

---

## 2026-10-25 (D1 · S1-15b 完成)

**推进**
- 实现 `stock_service.apply_txn`（库存唯一写入口）：锁行→查幂等→校验可用量→写余额→写流水，五步同事务
- 新增 ORM 模型（Inventory/StockTxn/Sku/Location，含 qty_available 生成列）
- 新增 DomainError + InventoryInsufficient 异常（code + detail）
- 四个用例全绿（正常入库/库存不足/并发/幂等），全套 7 个测试通过

**踩坑（2 个真实 bug，都是测试抓出来的）**
1. **校验 bug**：写成 `on_hand >= 需求`，应为「可用量(=on_hand-allocated) >= 需求」。否则「已分配一部分」的维度会超卖——这正是 TC-02 设计这个维度的目的
2. **asyncpg infinity 坑**：`date.max(9999-12-31)` 被 asyncpg 序列化成 PG 的 `infinity`，与 schema 字面量 `date '9999-12-31'` 不相等，唯一约束维度错配。解法：新增 `SentinelDate` 类型装饰器，bind_expression 时把 date.max 内联成字面量

**协作进展**
- B 看到我的审查结论后，主动更新线框图：采纳 3 待敲定点 + 5 补充点，新增「D3 待确认清单」
- 分歧基本已通过文档对齐，D3 只剩「库存查询页默认列」待定

**明天第一步**
- S1-08 OpenAPI 契约（把 api-list 翻译成 openapi.yaml，B 线框图已就绪）
- D3 当面评审（敲定默认列 + 冻结）

---

## 2026-10-25 (D1 · S1-08 完成)

**推进**
- 产出 `contracts/openapi.yaml`（OpenAPI 3.1）：28 操作 / 32 schema，覆盖 24 条 S1 + 3 条 AI 预留 + login
- 产出 `contracts/errors.md`：错误码枚举 + 中文提示 + 统一响应格式
- api-list 复制到 `contracts/`，与 README 规划对齐
- 规范校验通过（openapi-spec-validator），36 个引用无缺失

**关键设计落进契约**
- 幂等头 `Idempotency-Key`（receive/putaway/pick/ship 必须）、AI 治理头 `X-Agent-Run-Id`
- 无 POST /inventory：库存唯一写入口在作业层，红线在契约层落地
- O4 分配失败 409 detail 带 sku_code/batch_no/required/available/shortfall（与 TC-02 对齐）
- 库存查询页加 location_type 筛选（B 采纳的「收货即落账」连带项）

**明天第一步**
- D3 当面评审（敲定「库存查询页默认列」→ 冻结契约）
- 通知 B：契约就绪，可生成 TS 类型 + 搭 mock
- A 进 P1：把 24 条接口落到 FastAPI 路由

---
