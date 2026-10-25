<template>
  <div class="pda-outbound">
    <!-- ========== 模式切换 ========== -->
    <div class="mode-bar">
      <button type="button" class="mode-btn" :class="{ active: mode === 'pick' }" @click="switchMode('pick')">
        拣货
      </button>
      <button type="button" class="mode-btn" :class="{ active: mode === 'ship' }" @click="switchMode('ship')">
        发运
      </button>
    </div>

    <!-- ========== 待处理单据列表 ========== -->
    <div v-if="!working" class="list-area">
      <div v-if="loading" class="state-hint">加载中…</div>
      <div v-else-if="!orders.length" class="state-hint">
        {{ mode === 'pick' ? '暂无待拣货单据（ALLOCATED）' : '暂无待发运单据（PICKED）' }}
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
            <span>{{ o.customer_name || '—' }}</span>
            <span>总量 {{ o.total_qty ?? 0 }}</span>
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

      <template v-else>
        <!-- 拣货：按路径逐行填实拣数量 -->
        <ul v-if="mode === 'pick'" class="line-list">
          <li v-for="(line, idx) in planLines" :key="line.line_id ?? idx" class="line-card">
            <div class="line-head">
              <span class="line-seq">{{ idx + 1 }}</span>
              <span class="line-sku">{{ line.sku_code }}</span>
              <span class="line-name">{{ line.sku_name }}</span>
            </div>
            <div class="line-meta">
              <span>库位 {{ line.location_code || '—' }}</span>
              <span v-if="line.batch_no">批次 {{ line.batch_no }}</span>
              <span>应拣 {{ line.qty_required ?? 0 }}</span>
            </div>
            <div class="line-inputs">
              <div class="input-item">
                <span class="input-label">实拣</span>
                <el-input-number
                  v-model="qtyMap[line.line_id!]"
                  :min="0"
                  :precision="0"
                  :controls="false"
                  class="qty-input"
                />
              </div>
            </div>
          </li>
        </ul>

        <!-- 发运：填承运商 / 运单号 -->
        <div v-else class="ship-form">
          <div class="form-item">
            <span class="form-label">承运商</span>
            <el-input v-model="carrier" placeholder="如：顺丰" clearable />
          </div>
          <div class="form-item">
            <span class="form-label">运单号</span>
            <el-input v-model="trackingNo" placeholder="扫描或输入运单号" clearable />
          </div>
          <div class="ship-tip">拣货完成后发运，库存将在发运时正式扣减。</div>
        </div>

        <div class="submit-bar">
          <el-button type="primary" size="large" :loading="submitting" class="submit-btn" @click="submit">
            提交{{ mode === 'pick' ? '拣货' : '发运' }}
          </el-button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// PDA 出库作业：拣货 O5 + 发运 O6
// - 拣货：ALLOCATED 单据 → 拉取拣货路径（GET pick，按 pick_seq）→ 填实拣数量 → POST pick
// - 发运：PICKED 单据 → 填承运商/运单号 → POST ship
// - 幂等：点提交时生成一次 key，失败重试复用，成功清空
// - 失败对账：409 INVALID_STATUS_TRANSITION 先查状态，已达成目标则视为成功
// =============================================================================
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError, makeIdempotencyKey } from '@/api/client'
import type { components } from '@/api/schema'

type OutboundOrder = components['schemas']['OutboundOrder']
type OutboundOrderDetail = components['schemas']['OutboundOrderDetail']
type PickLine = components['schemas']['PickLine']
type Mode = 'pick' | 'ship'

const STATUS_TEXT: Record<string, string> = {
  DRAFT: '草稿',
  ALLOCATED: '已分配',
  PICKING: '拣货中',
  PICKED: '已拣货',
  SHIPPED: '已发运',
  CANCELLED: '已取消',
}
const STATUS_TAG: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  DRAFT: 'info',
  ALLOCATED: 'warning',
  PICKING: 'warning',
  PICKED: 'primary',
  SHIPPED: 'success',
  CANCELLED: 'info',
}

const mode = ref<Mode>('pick')
const loading = ref(false)
const orders = ref<OutboundOrder[]>([])

const working = ref(false)
const detailLoading = ref(false)
const detail = ref<OutboundOrderDetail | null>(null)
const planLines = ref<PickLine[]>([])
const submitting = ref(false)

const qtyMap = reactive<Record<number, number>>({})
const carrier = ref('')
const trackingNo = ref('')

let idemKey = ''

async function loadOrders() {
  loading.value = true
  try {
    const status = mode.value === 'pick' ? 'ALLOCATED' : 'PICKED'
    const { data } = await client.GET('/outbound-orders', {
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

async function openWork(order: OutboundOrder) {
  working.value = true
  detailLoading.value = true
  detail.value = null
  planLines.value = []
  idemKey = ''
  carrier.value = ''
  trackingNo.value = ''
  clearMap()

  try {
    // 单据详情（拿单号、客户等）
    const { data } = await client.GET('/outbound-orders/{id}', { params: { path: { id: order.id! } } })
    detail.value = data ?? null

    if (mode.value === 'pick') {
      // 拣货路径（按 pick_seq 排序）
      const plan = await client.GET('/outbound-orders/{id}/pick', { params: { path: { id: order.id! } } })
      planLines.value = plan.data?.lines ?? []
      for (const line of planLines.value) {
        if (line.line_id == null) continue
        qtyMap[line.line_id] = line.qty_required ?? 0
      }
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
  planLines.value = []
  idemKey = ''
}

function clearMap() {
  for (const k of Object.keys(qtyMap)) delete qtyMap[Number(k)]
}

function validate(): string | null {
  if (mode.value === 'pick') {
    if (!planLines.value.length) return '没有拣货明细'
    for (const line of planLines.value) {
      if (line.line_id == null) continue
      const qty = qtyMap[line.line_id] ?? 0
      if (qty < 0) return '实拣数量不能为负'
      if (qty > (line.qty_required ?? 0)) return `商品 ${line.sku_code} 实拣不能超过应拣`
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
  if (!idemKey) {
    idemKey = makeIdempotencyKey(
      detail.value.order_no ?? String(detail.value.id),
      mode.value === 'pick' ? 'PICK' : 'SHIP',
    )
  }

  const orderId = detail.value.id
  try {
    if (mode.value === 'pick') {
      const lines = planLines.value
        .filter((l) => l.line_id != null)
        .map((l) => ({
          line_id: l.line_id!,
          qty_actual: qtyMap[l.line_id!] ?? 0,
          qty_rejected: Math.max((l.qty_required ?? 0) - (qtyMap[l.line_id!] ?? 0), 0),
        }))

      await client.POST('/outbound-orders/{id}/pick', {
        params: { path: { id: orderId }, header: { 'Idempotency-Key': idemKey } },
        body: { lines },
      })
      ElMessage.success('拣货完成')
    } else {
      await client.POST('/outbound-orders/{id}/ship', {
        params: { path: { id: orderId }, header: { 'Idempotency-Key': idemKey } },
        body: {
          carrier: carrier.value.trim() || null,
          tracking_no: trackingNo.value.trim() || null,
        },
      })
      ElMessage.success('发运成功')
    }

    idemKey = ''
    closeWork()
    await loadOrders()
  } catch (e) {
    if (e instanceof ApiError && e.code === 'INVALID_STATUS_TRANSITION') {
      const ok = await recoverIfDone(orderId)
      if (ok) return
    }
    ElMessage.error(e instanceof ApiError ? e.message : '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

/** 409 后先对账：目标状态已达成则视为成功 */
async function recoverIfDone(orderId: number): Promise<boolean> {
  try {
    const { data } = await client.GET('/outbound-orders/{id}', { params: { path: { id: orderId } } })
    const target = mode.value === 'pick' ? 'PICKED' : 'SHIPPED'
    const status = data?.status
    if (status === target || (mode.value === 'ship' && status === 'SHIPPED')) {
      ElMessage.success(mode.value === 'pick' ? '拣货完成（上次已提交）' : '发运成功（上次已提交）')
      idemKey = ''
      closeWork()
      await loadOrders()
      return true
    }
  } catch {
    // 对账失败按原错误提示
  }
  return false
}

onMounted(loadOrders)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.pda-outbound {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 12px 14px 0;
  box-sizing: border-box;
}

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

.line-seq {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(74, 125, 224, 0.2);
  color: #9db8ec;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
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
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
}

.qty-input {
  width: 120px;
}

.ship-form {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 80px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  color: v.$text-secondary;
}

.ship-tip {
  font-size: 12px;
  color: v.$text-muted;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(74, 125, 224, 0.08);
}

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
