# WMS 三页面线框图提纲（D3 评审用）

> 作者：B · 日期 2026-10-25
> 铁律 1：库存字段只用【现有库存】【可用库存】，全文不出现其他同义词。
> 铁律 2：每项标注【PC】=电脑端 /【PDA】=手持端，用于确定接口幂等与异常提示。

---

## 页面 1：库存查询页

**① 顶部搜索 + 筛选（逐条）**
- 搜索：SKU 编码 / 名称 / 条码 模糊搜【PC】→ `sku.sku_code / name / barcode`
- 筛选：库位全码 / 库区【PC】→ `location.location_code / zone_code`
- 筛选：库位类型【PC】→ `location.location_type`（STORAGE / RECEIVING / PICKING / STAGING / QUARANTINE）
- 筛选：批次【PC】→ `inventory.batch_no`
- 筛选：效期预警 N 天内到期【PC】→ I1 的 `expiring_days`
- 筛选：只看有货（可用库存 > 0）【PC】

**② 列表展示字段（逐条）**
- SKU 编码 → `sku.sku_code`
- 商品名称 → `sku.name`
- 规格 → `sku.spec`
- 库位全码 → `location.location_code`
- 批次 → `inventory.batch_no`
- 效期 → `inventory.expiry_date`
- 【现有库存】→ `inventory.qty_on_hand`
- 已分配（锁定）→ `inventory.qty_allocated`
- 【可用库存】→ `inventory.qty_available`（生成列，只读）
- 单位 → `sku.base_uom`

**③ PC / PDA 入口**
- 【PC】完整查询 + 筛选 + 点行看流水（跳 I2）
- 【PDA】只读速查（P2 可选，不做操作）

---

## 页面 2：入库作业台（收货 → 上架）

### 环节 A：收货【PDA 现场 + PC 建单】
- 【PC】建单 / 改明细数量 / 看进度 / 取消（B2/B4/B7）
- 【PDA】扫码后展示：扫入库单 → 单头（供应商、应收合计）；扫 SKU 条码 → 商品名、规格、应收 `qty_required`、已收 `qty_actual`、剩余待收
- 【PDA】可录入：实收数、批次 `batch_no`（`is_batch_managed` 商品必填）、效期 `expiry_date`、不良数 `qty_rejected`
- 【PDA】提交：确认收货 → 入暂存位（RECEIVING），走 `apply_txn`(RECEIPT)，DRAFT→RECEIVED
- 部分收货后状态仍 RECEIVED（可继续收），全收完才 PUTAWAY

### 环节 B：上架【PDA 现场】
- 【PDA】扫码后展示：扫收货单 → 系统按策略给目标库位 `to_location_id`
- 【PDA】操作：扫实际库位码校验是否一致
- 【PDA】提交：确认上架 → 暂存位转存储位，走 `apply_txn`(PUTAWAY)，RECEIVED→PUTAWAY→DONE
- 幂等：receive / putaway 带 `Idempotency-Key`（PDA 弱网重试）

---

## 页面 3：出库作业台（分配 → 拣货 → 发运）

### 步骤 1：任务分配【PC】
- 建单 O2、**按明细行分配** O4（FEFO 锁批次，只动 `allocated_delta`，失败 409+明细）
- 取消 O7（DRAFT/ALLOCATED），ALLOCATED 回滚走 `DEALLOCATE`（`allocated_delta` 负）
- 列表字段：出库单号、客户、状态、优先级、要求发货日、总量

### 步骤 2：PDA 拣货【PDA 现场】
- 扫码后展示：扫出库单 → 拣货任务；返回路径按 `location.pick_seq` 排序
- 返回字段：SKU 编码、库位全码、应拣数、批次、效期
- 明细字段：应拣 `qty_required` / 实拣 `qty_actual` / 短拣 `qty_rejected`
- 操作：扫库位校验 → 扫 SKU → 输实拣数 → 逐行确认（`apply_txn` PICK：`allocated_delta` 负、`on_hand` 不动）

### 步骤 3：发运确认【PC】
- 确认发运 → 扣减 + 落 `stock_txn`(SHIP) → SHIPPED
- 录入：承运 `carrier` / 运单号 `tracking_no`
- 幂等：pick / ship 带 `Idempotency-Key`

---

## 预留补充字段空位（5 处）

1. 【补充位 1：＿＿＿＿＿＿】
2. 【补充位 2：＿＿＿＿＿＿】
3. 【补充位 3：＿＿＿＿＿＿】
4. 【补充位 4：＿＿＿＿＿＿】
5. 【补充位 5：＿＿＿＿＿＿】
