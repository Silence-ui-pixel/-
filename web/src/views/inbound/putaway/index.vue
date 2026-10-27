<template>
  <div class="putaway-progress">
    <!-- ========== 统计条（点击可切换筛选） ========== -->
    <section class="panel stats">
      <div
        v-for="s in statCards"
        :key="s.status"
        class="stat-card"
        :class="{ active: filters.status === s.status }"
        @click="pickStatus(s.status)"
      >
        <span class="stat-num" :class="`num-${s.tag}`">{{ s.count }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
      <div class="stat-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>上架执行在 <b>PDA 入库作业</b> 完成；本页只读，用于核对货最终落在哪个库位</span>
      </div>
    </section>

    <!-- ========== 筛选 ========== -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="单据状态">
          <el-select v-model="filters.status" style="width: 150px" @change="handleSearch">
            <el-option label="待上架" value="RECEIVED" />
            <el-option label="上架中" value="PUTAWAY" />
            <el-option label="已完成" value="DONE" />
            <el-option label="全部" value="ALL" />
          </el-select>
        </el-form-item>
        <el-form-item label="单据类型">
          <el-select v-model="filters.order_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="采购入库" value="PO" />
            <el-option label="退货入库" value="RETURN" />
            <el-option label="调拨入库" value="TRANSFER" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <!-- ========== 列表 ========== -->
    <section class="panel">
      <div class="panel-title">
        <span>入库单上架情况</span>
        <span class="panel-hint">共 {{ total }} 单 · 点击「查上架明细」看每行落到哪个库位</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无单据"
        :row-key="(r: InboundOrder) => r.id!"
        class="data-table"
      >
        <el-table-column prop="order_no" label="单据号" min-width="180">
          <template #default="{ row }">
            <span class="order-no">{{ row.order_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">{{ ORDER_TYPE_TEXT[row.order_type as string] ?? row.order_type }}</template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商" min-width="150">
          <template #default="{ row }">{{ row.supplier_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="应收 / 实收" width="130" align="center">
          <template #default="{ row }">
            <span class="qty">{{ row.total_expected_qty ?? 0 }}</span>
            <span class="qty-sep">/</span>
            <span class="qty-received">{{ row.total_received_qty ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收货时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ fmtTime(row.received_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :loading="detailLoadingId === row.id" @click="openDetail(row)">
              查上架明细
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadData"
        />
      </div>
    </section>

    <!-- ========== 上架明细抽屉 ========== -->
    <el-drawer v-model="drawerVisible" title="上架明细" size="760px" :destroy-on-close="true">
      <div v-if="detail" class="drawer-body">
        <!-- 单据头 -->
        <div class="detail-head">
          <div class="head-row">
            <span class="head-label">单据号</span>
            <span class="head-value mono">{{ detail.order_no }}</span>
            <el-tag :type="statusTag(detail.status)" size="small">{{ statusText(detail.status) }}</el-tag>
          </div>
          <div class="head-row">
            <span class="head-label">供应商</span>
            <span class="head-value">{{ detail.supplier_name || '—' }}</span>
            <span class="head-label ml">收货时间</span>
            <span class="head-value">{{ fmtTime(detail.received_at) }}</span>
          </div>
        </div>

        <!-- 上架进度汇总 -->
        <div class="progress-bar">
          <div class="progress-item">
            <span class="progress-num num-done">{{ putawayStat.done }}</span>
            <span class="progress-label">行已上架</span>
          </div>
          <div class="progress-item">
            <span class="progress-num num-pending">{{ putawayStat.pending }}</span>
            <span class="progress-label">行待上架</span>
          </div>
          <div class="progress-item">
            <span class="progress-num">{{ putawayStat.qtyPutaway }}</span>
            <span class="progress-label">已落位数量</span>
          </div>
        </div>

        <!-- 明细表 -->
        <el-table :data="detail.lines ?? []" size="small" class="data-table" :row-key="(r: OrderLine) => r.id!">
          <el-table-column label="行" width="56" align="center">
            <template #default="{ row }">{{ row.line_no }}</template>
          </el-table-column>
          <el-table-column prop="sku_code" label="SKU 编码" min-width="120">
            <template #default="{ row }">
              <span class="mono">{{ row.sku_code }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="sku_name" label="商品名称" min-width="150" show-overflow-tooltip />
          <el-table-column label="批次" width="130">
            <template #default="{ row }">
              <span class="mono">{{ row.batch_no || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="实收数量" width="100" align="right">
            <template #default="{ row }">{{ row.qty_actual ?? 0 }}</template>
          </el-table-column>
          <el-table-column label="上架目标库位" width="160">
            <template #default="{ row }">
              <span v-if="row.to_location_id" class="loc-code">
                {{ locationCode(row.to_location_id) }}
              </span>
              <el-tag v-else size="small" type="warning">待上架</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="行状态" width="100" align="center">
            <template #default="{ row }">
              <span :class="row.status === 'DONE' ? 'status-done' : 'status-open'">
                {{ LINE_STATUS_TEXT[row.status as string] ?? row.status }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <div class="drawer-foot">
          <el-icon><InfoFilled /></el-icon>
          <span>「待上架」表示已收货但尚未落位，需在 PDA 入库作业中执行上架</span>
        </div>
      </div>
      <div v-else class="drawer-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中…</span>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 上架进度（只读）
// - 上架动作在 PDA（/pda/inbound）执行，本页只做核对与追溯
// - 数据源：GET /inbound-orders（列表） + GET /inbound-orders/{id}（明细） + GET /locations（id→编码）
// - 关键字段：OrderLine.to_location_id —— 上架后落库，null 即「待上架」
// - 统计用 page_size=1 只取 meta.total，避免为三个状态各拉全量
// =============================================================================
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, Loading } from '@element-plus/icons-vue'
import { client, ApiError } from '@/api/client'
import type { components, paths } from '@/api/schema'

type InboundOrder = components['schemas']['InboundOrder']
type InboundOrderDetail = components['schemas']['InboundOrderDetail']
type OrderLine = components['schemas']['OrderLine']
type ListQuery = NonNullable<paths['/inbound-orders']['get']['parameters']['query']>
type Status = NonNullable<InboundOrder['status']>

const ORDER_TYPE_TEXT: Record<string, string> = {
  PO: '采购入库',
  RETURN: '退货入库',
  TRANSFER: '调拨入库',
}

const STATUS_TEXT: Record<Status, string> = {
  DRAFT: '草稿',
  ARRIVED: '已到货',
  RECEIVING: '收货中',
  RECEIVED: '待上架',
  PUTAWAY: '上架中',
  DONE: '已完成',
  CANCELLED: '已取消',
}

const STATUS_TAG: Record<Status, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  DRAFT: 'info',
  ARRIVED: 'warning',
  RECEIVING: 'warning',
  RECEIVED: 'warning',
  PUTAWAY: 'primary',
  DONE: 'success',
  CANCELLED: 'info',
}

const LINE_STATUS_TEXT: Record<string, string> = {
  OPEN: '待处理',
  ALLOCATED: '已分配',
  PARTIAL: '部分完成',
  DONE: '已完成',
  CANCELLED: '已取消',
}

const loading = ref(false)
const rows = ref<InboundOrder[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({
  status: 'RECEIVED' as 'RECEIVED' | 'PUTAWAY' | 'DONE' | 'ALL',
  order_type: '' as NonNullable<ListQuery['order_type']> | '',
})

/** 三个状态的单据数（page_size=1 只取 meta.total） */
const counts = reactive({ RECEIVED: 0, PUTAWAY: 0, DONE: 0 })

const statCards = computed(() => [
  { status: 'RECEIVED' as const, label: '待上架', count: counts.RECEIVED, tag: 'pending' },
  { status: 'PUTAWAY' as const, label: '上架中', count: counts.PUTAWAY, tag: 'doing' },
  { status: 'DONE' as const, label: '已完成', count: counts.DONE, tag: 'done' },
])

/* ---------- 明细抽屉 ---------- */
const drawerVisible = ref(false)
const detailLoadingId = ref<number | null>(null)
const detail = ref<InboundOrderDetail | null>(null)
/** 库位 id → 编码 */
const locationMap = ref<Map<number, string>>(new Map())

const putawayStat = computed(() => {
  const lines = detail.value?.lines ?? []
  let done = 0
  let pending = 0
  let qtyPutaway = 0
  for (const l of lines) {
    if (l.to_location_id) {
      done += 1
      qtyPutaway += Number(l.qty_actual ?? 0)
    } else {
      pending += 1
    }
  }
  return { done, pending, qtyPutaway }
})

function statusText(s: unknown): string {
  return STATUS_TEXT[s as Status] ?? String(s ?? '—')
}

function statusTag(s: unknown): 'primary' | 'success' | 'info' | 'warning' | 'danger' {
  return STATUS_TAG[s as Status] ?? 'info'
}

function locationCode(id?: number | null): string {
  if (!id) return '—'
  return locationMap.value.get(id) ?? `#${id}`
}

/** ISO 8601 UTC → 本地时间 */
function fmtTime(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadData() {
  loading.value = true
  try {
    const query: ListQuery = { page: page.value, page_size: pageSize.value }
    if (filters.status !== 'ALL') query.status = filters.status
    if (filters.order_type) query.order_type = filters.order_type

    const { data } = await client.GET('/inbound-orders', { params: { query } })
    rows.value = data?.items ?? []
    total.value = data?.meta?.total ?? rows.value.length
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载入库单失败')
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

/** 三个状态的计数（并行，page_size=1 减少传输） */
async function loadCounts() {
  const statuses: Array<'RECEIVED' | 'PUTAWAY' | 'DONE'> = ['RECEIVED', 'PUTAWAY', 'DONE']
  const results = await Promise.all(
    statuses.map((s) =>
      client
        .GET('/inbound-orders', { params: { query: { status: s, page: 1, page_size: 1 } } })
        .then((r) => r.data?.meta?.total ?? 0)
        .catch(() => 0),
    ),
  )
  counts.RECEIVED = results[0]
  counts.PUTAWAY = results[1]
  counts.DONE = results[2]
}

/** 库位 id → 编码（一次拉全量，13 条无分页） */
async function loadLocations() {
  try {
    const { data } = await client.GET('/locations')
    const map = new Map<number, string>()
    for (const l of data?.items ?? []) {
      if (l.id && l.location_code) map.set(l.id, l.location_code)
    }
    locationMap.value = map
  } catch {
    // 库位解析失败不阻塞主流程，回退显示 #id
  }
}

async function openDetail(row: InboundOrder) {
  if (!row.id) return
  detailLoadingId.value = row.id
  detail.value = null
  drawerVisible.value = true
  try {
    const { data } = await client.GET('/inbound-orders/{id}', { params: { path: { id: row.id } } })
    detail.value = data ?? null
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载上架明细失败')
    drawerVisible.value = false
  } finally {
    detailLoadingId.value = null
  }
}

function pickStatus(s: 'RECEIVED' | 'PUTAWAY' | 'DONE') {
  filters.status = filters.status === s ? 'ALL' : s
  handleSearch()
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handleReset() {
  filters.status = 'RECEIVED'
  filters.order_type = ''
  page.value = 1
  loadData()
}

onMounted(() => {
  loadData()
  loadCounts()
  loadLocations()
})
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.putaway-progress {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  background: rgba(24, 29, 42, 0.72);
  border: 1px solid v.$card-border;
  border-radius: 12px;
  padding: 16px 18px;
}

/* ---------- 统计条 ---------- */
.stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: baseline;
  gap: 7px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  &.active {
    background: rgba(74, 125, 224, 0.12);
    border-color: rgba(74, 125, 224, 0.45);
  }
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  color: v.$text-primary;

  &.num-pending {
    color: #f0a75a;
  }

  &.num-doing {
    color: #9db8ec;
  }

  &.num-done {
    color: #6fd39b;
  }
}

.stat-label {
  font-size: 12px;
  color: v.$text-muted;
}

.stat-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  padding-left: 16px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: v.$text-muted;

  b {
    color: #9db8ec;
    font-weight: 600;
  }
}

/* ---------- 筛选 / 列表 ---------- */
.toolbar {
  padding-bottom: 4px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 0;
}

.panel-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;
}

.panel-hint {
  font-size: 12px;
  font-weight: 400;
  color: v.$text-muted;
}

.order-no,
.mono {
  font-family: 'JetBrains Mono', Consolas, monospace;
  color: v.$text-primary;
}

.qty {
  color: v.$text-secondary;
}

.qty-sep {
  margin: 0 5px;
  color: v.$text-muted;
}

.qty-received {
  color: #6fd39b;
  font-weight: 600;
}

.time-text {
  font-size: 12px;
  color: v.$text-muted;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* ---------- 抽屉 ---------- */
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-head {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.head-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.head-label {
  color: v.$text-muted;
  font-size: 12px;

  &.ml {
    margin-left: 18px;
  }
}

.head-value {
  color: v.$text-primary;
}

.progress-bar {
  display: flex;
  gap: 28px;
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(74, 125, 224, 0.08);
  border: 1px solid rgba(74, 125, 224, 0.22);
}

.progress-item {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.progress-num {
  font-size: 20px;
  font-weight: 700;
  color: v.$text-primary;

  &.num-done {
    color: #6fd39b;
  }

  &.num-pending {
    color: #f0a75a;
  }
}

.progress-label {
  font-size: 12px;
  color: v.$text-muted;
}

.loc-code {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 4px;
  background: rgba(111, 211, 155, 0.12);
  color: #6fd39b;
}

.status-done {
  color: #6fd39b;
  font-size: 12px;
}

.status-open {
  color: #f0a75a;
  font-size: 12px;
}

.drawer-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: v.$text-muted;
}

.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 48px 0;
  font-size: 13px;
  color: v.$text-muted;
}
</style>
