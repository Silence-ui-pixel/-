<template>
  <div class="pda-inbound">
    <!-- ========== 模式切换 ========== -->
    <div class="mode-bar">
      <button type="button" class="mode-btn" :class="{ active: mode === 'receive' }" @click="switchMode('receive')">
        收货
      </button>
      <button type="button" class="mode-btn" :class="{ active: mode === 'putaway' }" @click="switchMode('putaway')">
        上架
      </button>
    </div>

    <!-- ========== 待处理单据列表 ========== -->
    <div v-if="!working" class="list-area">
      <div v-if="loading" class="state-hint">加载中…</div>
      <div v-else-if="!orders.length" class="state-hint">
        {{ mode === 'receive' ? '暂无待收货单据（DRAFT）' : '暂无待上架单据（RECEIVED）' }}
      </div>

      <ul v-else class="order-list">
        <li v-for="o in orders" :key="o.id" class="order-card" @click="openWork(o)">
          <div class="order-head">
            <span class="order-no">{{ o.order_no }}</span>
            <el-tag size="small" :type="STATUS_TAG[o.status ?? ''] ?? 'info'">
              {{ STATUS_TEXT[o.status ?? ''] ?? o.status }}
            </el-tag>
          </div>
          <div class="order-meta">
            <span>{{ o.supplier_name || '—' }}</span>
            <span>应收 {{ o.total_expected_qty ?? 0 }} / 实收 {{ o.total_received_qty ?? 0 }}</span>
          </div>
        </li>
      </ul>

      <el-button class="refresh-btn" size="large" :loading="loading" @click="loadOrders">刷新列表</el-button>
    </div>

    <!-- ========== 作业面板 ========== -->
    <div v-else class="work-panel">
      <div class="work-head">
        <button type="button" class="back-btn" @click="closeWork">← 返回</button>
        <span class="work-title">{{ detail?.order_no }}</span>
      </div>

      <div v-if="detailLoading" class="state-hint">加载单据…</div>

      <template v-else-if="detail">
        <!-- 上架模式：目标库位（可选，留空则系统自动分配） -->
        <div v-if="mode === 'putaway'" class="global-loc">
          <span class="loc-label">目标库位</span>
          <el-input v-model="targetLocation" placeholder="留空由系统分配" clearable />
        </div>

        <ul class="line-list">
          <li v-for="line in detail.lines ?? []" :key="line.id" class="line-card">
            <div class="line-head">
              <span class="line-sku">{{ line.sku_code }}</span>
              <span class="line-name">{{ line.sku_name }}</span>
            </div>
            <div class="line-meta">应收 {{ line.qty_required ?? 0 }} · 已收 {{ line.qty_actual ?? 0 }}</div>

            <!-- 收货：实收数量 + 批次号 -->
            <div v-if="mode === 'receive'" class="line-inputs">
              <div class="input-item">
                <span class="input-label">实收</span>
                <el-input-number v-model="qtyMap[line.id!]" :min="0" :precision="0" :controls="false" class="qty-input" />
              </div>
              <div v-if="isBatchManaged(line.sku_id)" class="input-item">
                <span class="input-label batch-required">批次*</span>
                <el-input v-model="batchMap[line.id!]" placeholder="批次号（必填）" />
              </div>
            </div>
          </li>
        </ul>

        <div class="submit-bar">
          <el-button type="primary" size="large" :loading="submitting" class="submit-btn" @click="submit">
            提交{{ mode === 'receive' ? '收货' : '上架' }}
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// PDA 入库作业：收货 B5 + 上架 B6
// - 列表：收货查 DRAFT 单，上架查 RECEIVED 单
// - 收货：逐行填实收数量，批次管理商品必须填批次号（否则后端 422）
// - 上架：可指定目标库位，留空则由系统按策略分配
// - 幂等：点提交时生成一次 key，失败重试复用（成功后清空）
// - 失败对账：409 INVALID_STATUS_TRANSITION 时先查单据状态，已达成目标则视为成功
// =============================================================================
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError, makeIdempotencyKey } from '@/api/client'
import type { components } from '@/api/schema'

type InboundOrder = components['schemas']['InboundOrder']
type InboundOrderDetail = components['schemas']['InboundOrderDetail']
type Sku = components['schemas']['Sku']
type Mode = 'receive' | 'putaway'

const STATUS_TEXT: Record<string, string> = {
  DRAFT: '草稿',
  ARRIVED: '已到货',
  RECEIVING: '收货中',
  RECEIVED: '已收货',
  PUTAWAY: '已上架',
  DONE: '已完成',
  CANCELLED: '已取消',
}
const STATUS_TAG: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  DRAFT: 'info',
  ARRIVED: 'warning',
  RECEIVING: 'warning',
  RECEIVED: 'primary',
  PUTAWAY: 'success',
  DONE: 'success',
  CANCELLED: 'info',
}

const mode = ref<Mode>('receive')
const loading = ref(false)
const orders = ref<InboundOrder[]>([])

const working = ref(false)
const detailLoading = ref(false)
const detail = ref<InboundOrderDetail | null>(null)
const submitting = ref(false)
const targetLocation = ref('')

/** 明细输入状态：line_id → 值 */
const qtyMap = reactive<Record<number, number>>({})
const batchMap = reactive<Record<number, string>>({})

/** SKU 信息（判断是否批次管理） */
const skuMap = reactive<Record<number, Sku>>({})

/** 幂等键：首次提交生成，重试复用，成功后清空 */
let idemKey = ''

async function loadSkus() {
  if (Object.keys(skuMap).length) return
  try {
    const { data } = await client.GET('/skus', { params: { query: { page: 1, page_size: 100 } } })
    for (const s of data?.items ?? []) {
      if (s.id != null) skuMap[s.id] = s
    }
  } catch {
    // 拉不到 SKU 时降级：不强制批次（后端仍会 422 兜底）
  }
}

async function loadOrders() {
  loading.value = true
  try {
    const status = mode.value === 'receive' ? 'DRAFT' : 'RECEIVED'
    const { data } = await client.GET('/inbound-orders', {
      params: { query: { status, page: 1, page_size: 50 } },
    })
    orders.value = data?.items ?? []
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载失败')
    orders.value = []
  } finally {
    loading.value = false
  }
}

async function switchMode(m: Mode) {
  if (mode.value === m) return
  mode.value = m
  closeWork()
  await loadOrders()
}

async function openWork(order: InboundOrder) {
  working.value = true
  detailLoading.value = true
  detail.value = null
  idemKey = ''
  targetLocation.value = ''
  clearInputs()

  try {
    const { data } = await client.GET('/inbound-orders/{id}', { params: { path: { id: order.id! } } })
    detail.value = data ?? null
    // 默认实收 = 应收 - 已收
    for (const line of data?.lines ?? []) {
      if (line.id == null) continue
      const remain = Math.max((line.qty_required ?? 0) - (line.qty_actual ?? 0), 0)
      qtyMap[line.id] = remain
      batchMap[line.id] = line.batch_no ?? ''
    }
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载详情失败')
    working.value = false
  } finally {
    detailLoading.value = false
  }
}

function closeWork() {
  working.value = false
  detail.value = null
  idemKey = ''
}

function clearInputs() {
  for (const k of Object.keys(qtyMap)) delete qtyMap[Number(k)]
  for (const k of Object.keys(batchMap)) delete batchMap[Number(k)]
}

function isBatchManaged(skuId?: number) {
  return skuId != null && !!skuMap[skuId]?.is_batch_managed
}

/** 提交前校验 */
function validate(): string | null {
  const lines = detail.value?.lines ?? []
  if (!lines.length) return '该单据没有明细'

  for (const line of lines) {
    if (line.id == null) continue
    if (mode.value === 'receive') {
      const qty = qtyMap[line.id] ?? 0
      if (qty < 0) return '实收数量不能为负'
      if (isBatchManaged(line.sku_id) && qty > 0 && !batchMap[line.id]?.trim()) {
        return `商品 ${line.sku_code} 是批次管理，必须填批次号`
      }
    }
  }
  return null
}

async function submit() {
  if (submitting.value || !detail.value?.id) return

  const err = validate()
  if (err) {
    ElMessage.warning(err)
    return
  }

  submitting.value = true
  // 幂等键：第一次提交时生成，重试复用同一个
  if (!idemKey) {
    idemKey = makeIdempotencyKey(detail.value.order_no ?? String(detail.value.id), mode.value === 'receive' ? 'RECEIVE' : 'PUTAWAY')
  }

  const orderId = detail.value.id
  try {
    if (mode.value === 'receive') {
      const lines = (detail.value.lines ?? [])
        .filter((l) => l.id != null)
        .map((l) => ({
          line_id: l.id!,
          qty_actual: qtyMap[l.id!] ?? 0,
          qty_rejected: 0,
          ...(batchMap[l.id!]?.trim() ? { batch_no: batchMap[l.id!].trim() } : {}),
        }))

      await client.POST('/inbound-orders/{id}/receive', {
        params: { path: { id: orderId }, header: { 'Idempotency-Key': idemKey } },
        body: { lines },
      })
      ElMessage.success('收货成功')
    } else {
      await client.POST('/inbound-orders/{id}/putaway', {
        params: { path: { id: orderId }, header: { 'Idempotency-Key': idemKey } },
        body: { lines: [] }, // 留空 → 全部由系统按策略分配
      })
      ElMessage.success('上架成功')
    }

    idemKey = ''
    closeWork()
    await loadOrders()
  } catch (e) {
    // 失败对账：状态机冲突极可能是「上次其实成功了，响应丢了」
    if (e instanceof ApiError && e.code === 'INVALID_STATUS_TRANSITION') {
      const recovered = await recoverIfDone(orderId)
      if (recovered) return
    }
    ElMessage.error(e instanceof ApiError ? e.message : '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

/** 409 后先对账：目标状态已达成则视为成功 */
async function recoverIfDone(orderId: number): Promise<boolean> {
  try {
    const { data } = await client.GET('/inbound-orders/{id}', { params: { path: { id: orderId } } })
    const target = mode.value === 'receive' ? 'RECEIVED' : 'PUTAWAY'
    const status = data?.status
    if (status === target || status === 'DONE' || (mode.value === 'putaway' && status === 'PUTAWAY')) {
      ElMessage.success(mode.value === 'receive' ? '收货成功（上次已提交）' : '上架成功（上次已提交）')
      idemKey = ''
      closeWork()
      await loadOrders()
      return true
    }
  } catch {
    // 对账失败就按原错误提示
  }
  return false
}

onMounted(async () => {
  await loadSkus()
  await loadOrders()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.pda-inbound {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 12px 14px 0;
  box-sizing: border-box;
}

/* ---------- 模式切换 ---------- */
.mode-bar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  margin-bottom: 12px;
}

.mode-btn {
  flex: 1;
  height: 42px;
  border-radius: 10px;
  border: 1px solid v.$card-border;
  background: rgba(255, 255, 255, 0.04);
  color: v.$text-secondary;
  font-size: 15px;
  cursor: pointer;

  &.active {
    background: rgba(74, 125, 224, 0.18);
    border-color: rgba(74, 125, 224, 0.55);
    color: #cddcff;
    font-weight: 600;
  }
}

/* ---------- 列表 ---------- */
.list-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 20px;
}

.order-list {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-card {
  padding: 14px;
  border-radius: 12px;
  background: rgba(24, 29, 42, 0.78);
  border: 1px solid v.$card-border;
  cursor: pointer;

  &:active {
    background: rgba(74, 125, 224, 0.12);
  }
}

.order-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.order-no {
  font-size: 15px;
  font-weight: 600;
  color: v.$text-primary;
}

.order-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
  font-size: 12px;
  color: v.$text-secondary;
}

.refresh-btn {
  width: 100%;
}

/* ---------- 作业面板 ---------- */
.work-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.work-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  margin-bottom: 12px;
}

.back-btn {
  border: none;
  background: transparent;
  color: v.$text-secondary;
  font-size: 14px;
  cursor: pointer;
}

.work-title {
  font-size: 15px;
  font-weight: 600;
  color: v.$text-primary;
}

.global-loc {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.loc-label {
  font-size: 13px;
  color: v.$text-secondary;
  white-space: nowrap;
}

.line-list {
  list-style: none;
  margin: 0;
  padding: 0 0 80px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.line-card {
  padding: 14px;
  border-radius: 12px;
  background: rgba(24, 29, 42, 0.78);
  border: 1px solid v.$card-border;
}

.line-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.line-sku {
  font-size: 15px;
  font-weight: 600;
  color: v.$text-primary;
}

.line-name {
  font-size: 13px;
  color: v.$text-secondary;
}

.line-meta {
  margin-top: 6px;
  font-size: 12px;
  color: v.$text-muted;
}

.line-inputs {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.input-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.input-label {
  font-size: 13px;
  color: v.$text-secondary;
  white-space: nowrap;

  &.batch-required {
    color: #f0a75a;
  }
}

.qty-input {
  width: 120px;
}

/* ---------- 提交栏 ---------- */
.submit-bar {
  position: sticky;
  bottom: 0;
  flex-shrink: 0;
  padding: 10px 0 16px;
  background: linear-gradient(to top, rgba(16, 20, 32, 0.98), rgba(16, 20, 32, 0));
}

.submit-btn {
  width: 100%;
}

.state-hint {
  margin-top: 40px;
  text-align: center;
  font-size: 14px;
  color: v.$text-muted;
}
</style>
