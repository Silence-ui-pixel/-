# 仓储智能管理 Agent 系统

> Sprint 1 · 领域与账务底座（成员 A 负责部分）

## 快速开始

```bash
# 1. 启动 db + api（首次会自动生成 .env、构建镜像）
bash scripts/dev.sh up

# 2. 建结构 + 播种（首次或重置后执行）
bash scripts/dev.sh db-init

# 3. 打开接口文档
#    http://127.0.0.1:8000/docs
```

装过 make 的话，`make up` / `make db-init` 完全等价（Makefile 只是转发到 `scripts/dev.sh`）。

**Windows 提示**：本机未装 make，直接用 `bash scripts/dev.sh <命令>`。Git Bash 自带 bash 和 curl，无需额外安装。

## 目录结构

```
Canku_project/
├── docker-compose.yml        本地编排：db + api（web 段已留占位，归 B）
├── Makefile                  薄封装，转发到 scripts/dev.sh
├── scripts/dev.sh            开发命令的唯一真源
├── .env.example              环境变量模板（.env 不进版本库）
├── .gitattributes            强制 LF，防 Windows CRLF 污染脚本
│
├── api/                      API 服务（FastAPI + SQLAlchemy async）
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini            迁移配置
│   ├── alembic/               迁移脚本（唯一真源）
│   │   └── versions/0001_baseline.py
│   ├── app/
│   │   ├── main.py           应用入口，路由挂载点
│   │   ├── core/config.py    配置（环境变量 > .env > 默认值）
│   │   ├── db/session.py     异步引擎 + Session 依赖
│   │   └── api/v1/health.py  存活 / 就绪探针
│   └── tests/                pytest
│
├── db/
│   ├── schema.sql            建结构（基线快照，仅供人工对照，不直接执行）
│   └── seed.sql              播种（可重复，幂等）
│
├── contracts/                协作契约，只有 A 能改（见其 README）
├── web/                      前端（Vue3 + Vite + TS + Element Plus），B 负责
│   ├── src/                  页面与组件（登录 / 工作台 / 入库 / 出库 / 库存 / PDA）
│   ├── package.json          npm run dev 启动
│   └── docs/                 B 的前端设计文档
│
├── A_project/                A 的独立工作区：任务、预检脚本、草稿
└── .github/workflows/ci.yml  CI：lint + 建库 + 幂等 + 对账 + 测试
```

## 常用命令

| 命令 | 作用 |
|---|---|
| `bash scripts/dev.sh up` | 起 db + api，等 API 就绪 |
| `bash scripts/dev.sh down` | 停止（数据保留），`down -v` 连数据一起删 |
| `bash scripts/dev.sh logs api` | 跟踪日志 |
| `bash scripts/dev.sh psql` | 进数据库终端 |
| `bash scripts/dev.sh db-init` | 迁移（alembic）+ 播种 |
| `bash scripts/dev.sh db-migrate` | 只跑迁移，不播种 |
| `bash scripts/dev.sh db-reset` | 清空重建（需输入 yes） |
| `bash scripts/dev.sh db-check` | 对账检查，非空即账实不一致 |
| `bash scripts/dev.sh test` | pytest |
| `bash scripts/dev.sh lint` / `fmt` | ruff |
| `bash scripts/dev.sh help` | 全部命令 |

## 设计文档

| 文件 | 说明 |
| --- | --- |
| `01-architecture.html` | 系统总体架构图（六层 + 治理 + 外部集成） |
| `02-kickoff-plan.html` | 启动方案与两人分工：14 周路线图、技术栈、协作机制、风险对策 |
| `03-data-model.html` | 领域模型：ER 图 + 8 张表逐字段说明 + 库存一致性机制 |
| `04-sprint1-board.html` | Sprint 1 分工看板：双泳道甘特、16 张任务卡、红线、验收 |
| `04-sprint1-tasks.csv` | 任务卡 CSV（UTF-8 BOM，可直接导入飞书 / TAPD） |
| `A_project/` | A 成员工作区：任务三分区、环境预检、草稿 |

## 架构分层

架构按「底座 → 感知 → 智能」自下而上分六层，任何一层可独立替换。

| 层 | 名称 | 职责 | 关键点 |
| --- | --- | --- | --- |
| L1 | 接入层 | Web 工作台、PDA、大屏、语音/IM、开放 API | 同一套能力多端暴露 |
| L2 | AI Agent 智能层 | 编排器 + 专业 Agent + 治理链 + MCP 工具层 | 核心差异化，LLM 不直接持有写权限 |
| L3 | 业务应用层 | 入库、出库、库内作业、盘点、库存台账 | WMS 底座 |
| L4 | 算法与策略层 | 库位分配、波次、拣货路径、需求预测 | 确定性运筹优化，与 LLM 推理分离 |
| L5 | 数据层 | 关系库、缓存、向量库、时序库、对象存储 | 三类存储各司其职 |
| L6 | 感知与设备层 | 条码、RFID、PTL、AGV、温湿度、称重、视觉 | 实时性与幂等性是工程难点 |

横向治理：RBAC、审计追溯、AI 护栏、可观测与告警、容灾备份。

## 核心设计原则

**智能与操作权限分离。** AI 可以在策略包络内自适应推理，但任何改变实物状态的动作都必须经过确定性校验、显式人工审批、事后可审计。Agent 只输出「类型化的建议」，由决策引擎判定，人审批后交给执行器写入。

## 数据模型的三条铁律

1. 库存只有一个写入口（`stock_service`），禁止任何模块直接 UPDATE `inventory`
2. 改余额与写 `stock_txn` 必须在同一事务内，并带 before/after 快照
3. `stock_txn` 只追加，数据库触发器拒绝 UPDATE / DELETE

三条铁律都有测试守着：CI 里每次都会跑「对账必须全 OK」和「历史流水不可篡改」。

日常巡检：

```bash
bash scripts/dev.sh db-check
```

## 数据库验证

| 方式 | 命令 | 说明 |
|---|---|---|
| 容器内迁移 | `bash scripts/dev.sh db-migrate` | alembic 迁移，DDL 版本化 |
| 迁移 + 播种 | `bash scripts/dev.sh db-init` | 迁移 + seed，一条命令建全套 |
| Docker 全量验证 | `bash A_project/checklists/verify-schema.sh` | 起临时库跑 6 步断言，真实 PG 16 |
| 离线快速验证 | `node A_project/checklists/verify-offline.cjs` | PGlite，无需 Docker |

**注意**：`schema.sql` 与 `seed.sql` 故意分开。DDL 只该跑一次，种子要能反复跑；混在一个文件里就只能二选一，或者把 DDL 改成 `create table if not exists`（那会掩盖结构不一致，更危险）。

**DDL 的唯一真源是 `api/alembic/versions/`**（S1-06 接入）。`db/schema.sql` 保留作为「基线快照」供人工对照，**不再直接执行**——改表结构必须写新的 alembic 迁移脚本，而不是改 schema.sql。

## 后续产物（规划）

- `contracts/openapi.yaml` — OpenAPI 契约（S1-08）

> S1-06（alembic 迁移）、S1-07（接口清单）已完成，见 `A_project/drafts/`。

## 导出为图片

浏览器打开 `01-architecture.html` → `Ctrl + P` → 另存为 PDF，得到矢量图，可直接插入 PPT。
