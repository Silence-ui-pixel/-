<template>
  <div class="inventory-txn">
    <!-- ============ 筛选 ============ -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="SKU 编码">
          <el-input v-model="filters.sku_code" placeholder="编码或条码" clearable style="width: 160px" />
        </el-form-item>

        <el-form-item label="流水类型">
          <el-select v-model="filters.txn_type" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="(t, k) in TXN_TYPE_TEXT" :key="k" :label="t" :value="k" />
          </el-select>
        </el-form-item>

        <el-form-item label="来源">
          <el-select v-model="filters.source" placeholder="全部" clearable style="width: 120px">
            <el-option v-for="(t, k) in SOURCE_TEXT" :key="k" :label="t" :value="k" />
          </el-select>
        </el-form-item>

        <el-form-item label="时间">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 250px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <!-- ============ 列表 ============ -->
    <section class="panel">
      <div class="panel-title">
        <span>库存流水</span>
        <span class="panel-hint">只追加账本 · 不可修改（撤销请走单据反向流水）</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无流水记录"
        :row-key="(r: StockTxnItem) => r.id!"
        class="data-table"
      >
        <el-table-column label="时间" width="150">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="txn_no" label="流水号" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="TXN_TYPE_TAG[row.txn_type!] ?? 'info'" size="small">
              {{ TXN_TYPE_TEXT[row.txn_type!] ?? row.txn_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sku_code" label="SKU" min-width="110" />
        <el-table-column label="库位" min-width="130">
          <template #default="{ row }">{{ row.location_code || '—' }}</template>
        </el-table-column>
        <el-table-column label="批次" min-width="110">
          <template #default="{ row }">{{ row.batch_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="现有量变动" width="110" align="right">
          <template #default="{ row }">
            <span :class="deltaClass(row.on_hand_delta)">{{ fmtDelta(row.on_hand_delta) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分配量变动" width="110" align="right">
          <template #default="{ row }">
            <span :class="deltaClass(row.allocated_delta)">{{ fmtDelta(row.allocated_delta) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="变动后现有量" width="120" align="right">
          <template #default="{ row }">{{ row.after_on_hand ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="来源" width="80" align="center">
          <template #default="{ row }">{{ SOURCE_TEXT[row.source!] ?? row.source }}</template>
        </el-table-column>
        <el-table-column label="备注" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '—' }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadData"
          @size-change="onSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 库存流水页（I2）：只读账本
// - 契约红线：stock_txn 只追加，数据库触发器禁止 UPDATE/DELETE；页面**不提供任何编辑入口**
// - 撤销只能走单据反向流水（如取消单 → DEALLOCATE），不能改历史
// - 类型全部来自契约（components / paths）
// =============================================================================
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components, paths } from '@/api/schema'

type StockTxnItem = components['schemas']['StockTxnItem']
type StockTxnQuery = NonNullable<paths['/stock-txn']['get']['parameters']['query']>

const TXN_TYPE_TEXT: Record<string, string> = {
  RECEIPT: '收货',
  PUTAWAY: '上架',
  PICK: '拣货',
  SHIP: '发运',
  ADJUST: '调整',
  TRANSFER_IN: '移入',
  TRANSFER_OUT: '移出',
  COUNT_ADJUST: '盘点调整',
  ALLOCATE: '分配',
  DEALLOCATE: '取消分配',
}

const TXN_TYPE_TAG: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  RECEIPT: 'success',
  PUTAWAY: 'success',
  TRANSFER_IN: 'success',
  PICK: 'warning',
  SHIP: 'warning',
  TRANSFER_OUT: 'warning',
  ALLOCATE: 'primary',
  DEALLOCATE: 'primary',
  ADJUST: 'info',
  COUNT_ADJUST: 'info',
}

const SOURCE_TEXT: Record<string, string> = {
  WEB: 'PC',
  PDA: 'PDA',
  AGENT: 'AI',
  SYSTEM: '系统',
  IMPORT: '导入',
}

const loading = ref(false)
const rows = ref<StockTxnItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<[string, string] | null>(null)

const filters = reactive({
  sku_code: '',
  txn_type: '' as NonNullable<StockTxnQuery['txn_type']> | '',
  source: '' as NonNullable<StockTxnQuery['source']> | '',
})

async function loadData() {
  loading.value = true
  try {
    const query: StockTxnQuery = { page: page.value, page_size: pageSize.value }
    if (filters.sku_code) query.sku_code = filters.sku_code.trim()
    if (filters.txn_type) query.txn_type = filters.txn_type
    if (filters.source) query.source = filters.source
    if (dateRange.value?.[0]) query.from = dateRange.value[0]
    // 结束日期补到当天 23:59:59，避免漏掉当天数据
    if (dateRange.value?.[1]) query.to = `${dateRange.value[1]}T23:59:59`

    const { data } = await client.GET('/stock-txn', { params: { query } })
    rows.value = data?.items ?? []
    total.value = data?.meta?.total ?? 0
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '查询失败，请稍后重试')
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handleReset() {
  filters.sku_code = ''
  filters.txn_type = ''
  filters.source = ''
  dateRange.value = null
  page.value = 1
  loadData()
}

function onSizeChange() {
  page.value = 1
  loadData()
}

/** 变动量展示：+N / -N / 0 */
function fmtDelta(v?: number | null) {
  if (v == null) return '—'
  if (v === 0) return '0'
  return v > 0 ? `+${v}` : `${v}`
}

/** 变动量颜色：增加绿、减少橙、零灰 */
function deltaClass(v?: number | null) {
  if (v == null || v === 0) return 'delta-zero'
  return v > 0 ? 'delta-up' : 'delta-down'
}

/** ISO 8601 UTC → 本地时间展示 */
function fmtTime(iso?: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.inventory-txn {
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

.filter-form {
  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;
  }
  :deep(.el-form-item__label) {
    color: v.$text-secondary;
  }
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;

  .panel-hint {
    font-size: 12px;
    font-weight: 400;
    color: v.$text-muted;
  }
}

.data-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.03);
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-text-color: #{v.$text-primary};
  --el-table-header-text-color: #{v.$text-secondary};
  --el-table-row-hover-bg-color: rgba(74, 125, 224, 0.1);
}

/* 变动量颜色：增加绿 / 减少橙 / 零灰 */
.delta-up {
  color: #6fd39b;
  font-weight: 600;
}
.delta-down {
  color: #f0a75a;
  font-weight: 600;
}
.delta-zero {
  color: v.$text-muted;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
