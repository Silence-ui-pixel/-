# S1-15a apply_txn 测试用例设计（只写断言，不写实现）

> 状态：待评审（与 api-list 一起在 D3 过）
> 用途：S1-15b 实现前的「红」测试。**先写断言让测试全红，再实现让它全绿。**
> 原则：测行为不测实现细节。四个用例对应四个真实会出事故的场景。

---

## 〇、apply_txn 的契约（实现前必须一致）

`apply_txn` 是库存**唯一写入口**，所有库存变动都必须经过它。它做五件事，**必须在一个事务里**：

```
1. SELECT ... FOR UPDATE 锁住 inventory 行（按 sku+location+batch+expiry 唯一维度）
2. 校验：可用量 ≥ 需求（出库/分配场景），否则抛 INVENTORY_INSUFFICIENT
3. 写 inventory：更新 qty_on_hand / qty_allocated，version + 1
4. 写 stock_txn：落一条流水（before/after 快照 + 两个 delta）
5. COMMIT（任一步失败整体回滚）
```

**入参（函数签名草案，评审时可调）：**

```
apply_txn(
  txn_no:        str        # 幂等键，业务单号 + 序号，如 'SO-001-PICK'
  txn_type:      str        # RECEIPT/PUTAWAY/PICK/SHIP/ALLOCATE/DEALLOCATE/...
  sku_id:        int
  location_id:   int
  batch_no:      str
  expiry_date:   date
  on_hand_delta: Decimal    # 现有量变化，入 +、出 -
  allocated_delta: Decimal  # 分配量变化，分配 +、拣货 -
  ref_type:      str | None # INBOUND/OUTBOUND/COUNT/MANUAL
  ref_id:        int | None
  ref_line_id:   int | None
  source:        str        # WEB/PDA/AGENT/SYSTEM/IMPORT
  operator_id:   int | None
  agent_run_id:  str | None
  remark:        str | None
) -> stock_txn
```

> 注意 `before_on_hand` / `after_on_hand` 不在入参里 —— **由服务端在锁内读取并计算**，客户端传快照是不可信的（会被并发绕过）。这是实现要守的硬约束，测试用「快照自洽」断言兜底。

---

## 一、用例 TC-01 正常入库（RECEIPT）

**目标**：一条合法的入库流水能正确落账，余额与流水同步增长。

**前置**：空库（无该维度 inventory 行）。

| 项 | 值 |
|---|---|
| 输入 | txn_type=RECEIPT, on_hand_delta=+100, allocated_delta=0, sku/location/batch/expiry 取种子值 |
| 期望返回 | stock_txn 对象，含生成的 id、txn_no、before=0、after=100 |

**断言清单：**

| # | 断言 | 类型 |
|---|---|---|
| 1 | 返回的 `before_on_hand == 0` 且 `after_on_hand == 100` | 返回值 |
| 2 | `inventory` 表出现该维度 1 行，`qty_on_hand == 100`，`qty_allocated == 0`，`qty_available == 100` | DB |
| 3 | `inventory.version == 1` | DB |
| 4 | `stock_txn` 表恰好 1 行，`on_hand_delta == 100`，`allocated_delta == 0` | DB |
| 5 | `v_inventory_recon` 对该维度返回 `OK`（余额=流水累计，无 MISMATCH） | DB |

**边界补充（评审时确认是否纳入）**：入库时 `inventory` 行不存在（该维度首次入库）应自动 INSERT，而不是报错。这是冷库/新品首次入库的必然场景，**建议纳入 TC-01 作为第 6 条断言**。

---

## 二、用例 TC-02 库存不足（INVENTORY_INSUFFICIENT）

**目标**：扣减量 > 可用量时必须拒绝，且**不产生任何副作用**。

**前置**：某维度 `qty_on_hand=50, qty_allocated=20`（可用量 30）。

| 项 | 值 |
|---|---|
| 输入 | txn_type=SHIP, on_hand_delta=-40（需求 40 > 可用 30） |
| 期望 | 抛业务异常，错误码 `INVENTORY_INSUFFICIENT` |

**断言清单：**

| # | 断言 | 类型 |
|---|---|---|
| 1 | 抛出的异常 `code == "INVENTORY_INSUFFICIENT"` | 异常 |
| 2 | 异常 `detail` 里含需求量 40、可用量 30、差异 10（供前端展示） | 异常 |
| 3 | `inventory` 该行**数值未变**：qty_on_hand 仍 50、qty_allocated 仍 20、version 仍原值 | DB |
| 4 | `stock_txn` **没有新增行**（失败不留脏流水） | DB |

> **关键语义**：可用量 = `qty_on_hand - qty_allocated`，不是只减 on_hand。测试要专门用「已分配一部分」的维度来验，避免实现者误把校验写成 `on_hand >= 需求`。

---

## 三、用例 TC-03 并发扣减（行锁防超卖）

**目标**：两个并发事务扣减同一维度时，**总扣减不得超过可用量**。

**前置**：某维度 `qty_on_hand=10, qty_allocated=0`（可用量 10）。

| 项 | 值 |
|---|---|
| 场景 | 两个连接同时各 `on_hand_delta=-8`（合计 -16 > 可用 10） |
| 期望 | 恰好一个成功、一个失败；库存不为负 |

**断言清单：**

| # | 断言 | 类型 |
|---|---|---|
| 1 | 两个事务**恰好一个成功、一个抛 INVENTORY_INSUFFICIENT** | 异常 |
| 2 | 最终 `qty_on_hand == 2`（10-8），**不为负**，`ck_inv_on_hand` 未触发 | DB |
| 3 | `stock_txn` 恰好 1 行成功流水（delta=-8），失败的没留痕 | DB |
| 4 | 成功流的 `before_on_hand==10, after_on_hand==2`，快照自洽 | DB |

**实现注意（写进实现注释，不进测试）**：必须 `SELECT ... FOR UPDATE` 锁行后再读可用量再扣。若实现用「先读可用量再 UPDATE WHERE qty>=需求」的乐观方式，本用例会以极小概率偶发通过，**要用两个连接 + 显式栅栏（barrier）保证真实并发**，不能只是顺序跑两次。

---

## 四、用例 TC-04 重复提交（幂等）

**目标**：同一个 `txn_no` 重复提交，**只生效一次**，第二次返回原结果。

**前置**：空库。

| 项 | 值 |
|---|---|
| 场景 | 相同 txn_no='SO-001-PICK' 调 apply_txn 两次，参数完全相同 |
| 期望 | 第二次返回与第一次相同的 txn 记录，不重复扣减 |

**断言清单：**

| # | 断言 | 类型 |
|---|---|---|
| 1 | 两次调用返回的 `stock_txn.id` **相同**（同一条记录） | 返回值 |
| 2 | `inventory` 该维度 `qty_on_hand` 只被扣了**一次**（不是双倍） | DB |
| 3 | `stock_txn` 表该 txn_no **只有 1 行**（uk_txn_no 未违背，也未新增） | DB |

> **为什么必须幂等**：PDA 在仓库网络抖动时，同一单会重复提交。没有幂等，一次网络重试 = 一次重复扣库存，账直接就错了。`txn_no` 的唯一约束 `uk_txn_no` 是数据库层兜底，但实现应在锁内先查 `txn_no` 是否已存在，命中直接返回，而不是等唯一约束抛异常。

---

## 五、用例覆盖矩阵（一眼看全）

| 场景 | TC-01 正常入库 | TC-02 库存不足 | TC-03 并发 | TC-04 幂等 |
|---|---|---|---|---|
| 余额增长 | ✅ | — | — | — |
| 余额扣减 | — | ✅ 拒绝 | ✅ 只到上限 | ✅ 只一次 |
| 快照自洽 | ✅ | — | ✅ | ✅ |
| 流水落账 | ✅ 1 行 | ✅ 0 行 | ✅ 1 行 | ✅ 1 行 |
| 异常语义 | — | ✅ 错误码+明细 | ✅ 一成一败 | — |
| 并发安全 | — | — | ✅ 行锁 | — |
| 幂等 | — | — | — | ✅ txn_no |

---

## 六、四个用例之外，明确「不测什么」

（避免测试变负担，评审时确认）

1. **不测 SQL 层面已经由约束保证的事**：负库存（`ck_inv_on_hand`）、快照自洽（`ck_txn_snapshot`）、流水只追加（触发器）——这些 `verify-schema.sh` 已验，apply_txn 单测重复测是浪费。
2. **不测 FEFO 批次选择**：那是 `allocate` 的算法，不是 `apply_txn` 的职责。apply_txn 收到明确的 batch_no/expiry 就按它执行，选择权在上层。
3. **不测权限**：谁能调 apply_txn 是路由层的鉴权，不是事务函数职责。

---

## 七、给实现的落地提示（S1-15b 参考）

- 用 `asyncpg`/SQLAlchemy 时，`FOR UPDATE` 必须在**同一事务**里且不能 `autocommit`；测试要能开两个独立连接/会话。
- 幂等查询要放在**锁之后**（先锁行再查 txn_no），否则两个并发同 txn_no 仍可能双写。
- 异常用自定义 `DomainError(code, message, detail)` 抛，别用裸 `ValueError`，否则 TC-02 的断言拿不到 code。
- `before/after` 快照在锁内读 `inventory.qty_on_hand` 现算，**绝不信任入参**。

---

*下一步：D3 评审通过后，S1-15b 把这四个用例写成 `pytest`（先红后绿），并补齐 TC-01 第 6 条「首次入库自动建 inventory 行」的确认结论。*
