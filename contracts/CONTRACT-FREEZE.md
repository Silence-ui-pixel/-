# 契约冻结声明

> **版本：v1.0** ｜ **冻结日期：2026-10-25** ｜ **git tag：`contract-v1.0`**
> 冻结人：A（后端/契约）、B（前端/消费方）
> 决议全文：`A_project/with_B/D3-评审决议.md`

---

## 一、冻结范围

| 项 | 内容 | 数量 |
|---|---|---|
| 领域模型 | `db/schema.sql` 的 8 张表 + `v_inventory_recon` 视图 + 只追加触发器 | 8 表 / 1 视图 |
| API 契约 | `contracts/openapi.yaml` | 23 条路径 / 27 个操作 |
| 错误码 | `contracts/errors.md` | 19 个码 |
| 写操作入口 | `api/app/services/stock_service.py` 的 `apply_txn` | 唯一入口 |

冻结的 8 张表：`app_user`、`sku`、`location`、`inventory`、`stock_txn`、`inbound_order`、`outbound_order`、`order_line`。

---

## 二、冻结意味着什么

### 允许（不需要升版本，记为 v1.x）

- 新增接口
- schema 新增**可选**字段（不破坏已有调用方）
- 新增可选查询参数
- 新增错误码（明确触发场景）
- 文档、注释、测试补充

### 需要升 minor 版本（v1.0 → v2.0）+ 两人确认

- 修改已有字段的**语义或类型**
- 修改已有接口的**行为**（如 D2 分配改按明细行、C6 幂等改重放返回）
- 删除字段/接口
- 修改错误码的 HTTP 状态或含义

### 绝对不允许（除非全部推倒重来）

- 新增第二个库存写入口（绕过 `apply_txn`）
- 允许 `stock_txn` 的 UPDATE / DELETE
- 前端提交 `qty_available`
- 契约里出现「直接改库存」类接口

---

## 三、变更流程（五人以下小团队版，别搞成 RFC）

| 步骤 | 动作 | 产出 |
|---|---|---|
| 1 | 提出方在 `contracts/CHANGELOG.md` 写一条「待批准」 | 变更条目 |
| 2 | 判断属于上面哪一类（允许 / 需升版本 / 禁止） | — |
| 3 | 需升版本的：两人确认后改 `openapi.yaml` + 同步代码与测试 | 代码 + 契约 |
| 4 | 跑全量测试 + `openapi-spec-validator` 校验 | 全绿 |
| 5 | 打新 tag（`contract-v1.1` / `v2.0`） | tag |
| 6 | 更新本文第二节的版本号 | 本文件 |

**唯一例外**：导致数据错误（账实不符、超卖）的缺陷，直接修，事后补 CHANGELOG。

---

## 四、真源优先级（冲突时按这个裁决）

```
contracts/openapi.yaml   ← 接口契约唯一真源
        ↓
api/alembic/versions/    ← 表结构唯一真源（schema.sql 只是基线快照）
        ↓
api/app/                 ← 实现，必须符合上面两者
```

**代码与契约不一致时，改代码，不改契约。** 唯一例外是按第三节流程正式升版本。

---

## 五、冻结时的实现状态（诚实记录，避免后人误解）

契约里的这些条款在冻结时**已完整实现**：

- 23 条路径全部可用（2 条 AI 接口按设计返回 501 占位）
- 错误响应统一 `{code, message, detail}`（三个异常处理器全覆盖）
- `apply_txn` 唯一写入口 + 行锁 + `txn_no` 幂等
- 账实一致：`v_inventory_recon` 零异常

这些条款**已定义但未完整实现**（已记录，不阻塞冻结）：

| 条款 | 状态 | 计划 |
|---|---|---|
| `Idempotency-Key` 重放校验 | 接收但不校验 | Sprint 2，升 v1.1 |
| 分配按明细行（部分成功） | 当前整单 409 | Sprint 2，升 v1.1 |
| 跨批次分配 | 不支持 | Sprint 2 |
| 3 条 AI 接口 | 返回 501 | P2 |

> 为什么允许带欠账冻结：这些欠账**不影响账务正确性**（库存不会错），只影响体验和效率。把它们明确写在这里，比假装已实现更安全——后来者能一眼看到边界在哪。

---

## 六、验证方式（任何人可复核）

```bash
# 1. 契约合法性
docker cp contracts/openapi.yaml canku-api:/tmp/openapi.yaml
docker exec canku-api python -c "import yaml;from openapi_spec_validator import validate;validate(yaml.safe_load(open('/tmp/openapi.yaml',encoding='utf-8')));print('OK')"

# 2. 全量测试（当前 64 个）
docker exec canku-api python -m pytest -q

# 3. 账实一致
bash scripts/dev.sh db-check

# 4. 回到冻结时刻的契约
git checkout contract-v1.0 -- contracts/
```
