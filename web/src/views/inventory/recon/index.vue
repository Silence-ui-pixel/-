<template>
  <div class="inventory-recon">
    <!-- ========== 汇总 + 状态 tab ========== -->
    <section class="panel head-panel">
      <div class="summary">
        <span class="summary-item">
          <span class="dot dot-ok"></span>
          一致 <strong>{{ countOf('OK') }}</strong>
        </span>
        <span class="summary-item">
          <span class="dot" :class="abnormalCount > 0 ? 'dot-bad' : 'dot-ok'"></span>
          异常 <strong :class="{ 'text-bad': abnormalCount > 0 }">{{ abnormalCount }}</strong>
        </span>
        <span class="summary-total">共 {{ rows.length }} 条对账维度</span>
      </div>

      <div class="tab-bar">
        <button
          v-for="t in tabs"
          :key="t.value"
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === t.value }"
          @click="activeTab = t.value"
        >
          {{ t.label }}
          <span class="tab-count">{{ t.count }}</span>
        </button>
      </div>
    </section>

    <!-- ========== 列表 ========== -->
    <section class="panel">
      <div class="panel-title">
        <span>对账明细</span>
        <span class="panel-hint">库存余额 vs 流水累计 · 差异非 0 即异常</span>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredRows"
        empty-text="暂无对账数据"
        :row-key="(r: ReconItem) => `${r.sku_id}-${r.location_id}-${r.batch_no}`"
        :row-class-name="rowClassName"
        class="data-table"
      >
        <el-table-column prop="sku_code" label="SKU" min-width="110" />
        <el-table-column prop="sku_name" label="名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.sku_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="location_code" label="库位" min-width="100">
          <template #default="{ row }">
            <span class="loc-code">{{ row.location_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="批次" min-width="110">
          <template #default="{ row }">{{ row.batch_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="效期" width="110">
          <template #default="{ row }">{{ fmtExpiry(row.expiry_date) }}</template>
        </el-table-column>
        <el-table-column label="库存现有" width="100" align="right">
          <template #default="{ row }">{{ row.inv_on_hand ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="流水累计" width="100" align="right">
          <template #default="{ row }">{{ row.txn_on_hand ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="差异" width="90" align="right">
          <template #default="{ row }">
            <span :class="diffClass(row.diff_on_hand)">{{ fmtDiff(row.diff_on_hand) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="RECON_TAG[row.recon_status!] ?? 'info'" size="small">
              {{ RECON_TEXT[row.recon_status!] ?? row.recon_status }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 库存对账页（MANAGER/ADMIN）
// - 接口：GET /inventory/recon（无分页，返回 { items }）
// - recon_status 四种：OK / MISMATCH / ONLY_INVENTORY / ONLY_TXN
// - 一次查全量，前端算各状态数量并做 tab 过滤（避免多次请求）
// - v1.3 起 ReconItem 已带 sku_code / sku_name / location_code，无需前端 join
// =============================================================================
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components } from '@/api/schema'

type ReconItem = components['schemas']['ReconItem']
type ReconStatus = NonNullable<ReconItem['recon_status']>
type TabValue = 'ALL' | ReconStatus

const RECON_TEXT: Record<string, string> = {
  OK: '一致',
  MISMATCH: '数量不符',
  ONLY_INVENTORY: '仅有余额',
  ONLY_TXN: '仅有流水',
}

const RECON_TAG: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  OK: 'success',
  MISMATCH: 'danger',
  ONLY_INVENTORY: 'danger',
  ONLY_TXN: 'danger',
}

const loading = ref(false)
const rows = ref<ReconItem[]>([])
const activeTab = ref<TabValue>('ALL')

function countOf(status: ReconStatus): number {
  return rows.value.filter((r) => r.recon_status === status).length
}

const abnormalCount = computed(() => rows.value.filter((r) => r.recon_status !== 'OK').length)

const tabs = computed(() => [
  { value: 'ALL' as TabValue, label: '全部', count: rows.value.length },
  { value: 'OK' as TabValue, label: '一致', count: countOf('OK') },
  { value: 'MISMATCH' as TabValue, label: '数量不符', count: countOf('MISMATCH') },
  { value: 'ONLY_INVENTORY' as TabValue, label: '仅有余额', count: countOf('ONLY_INVENTORY') },
  { value: 'ONLY_TXN' as TabValue, label: '仅有流水', count: countOf('ONLY_TXN') },
])

const filteredRows = computed(() =>
  activeTab.value === 'ALL' ? rows.value : rows.value.filter((r) => r.recon_status === activeTab.value),
)

async function loadData() {
  loading.value = true
  try {
    const { data } = await client.GET('/inventory/recon')
    rows.value = data?.items ?? []
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载对账数据失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

/** 差异展示：+N / -N / 0 */
function fmtDiff(v?: number | null) {
  if (v == null || v === 0) return '0'
  return v > 0 ? `+${v}` : `${v}`
}

function diffClass(v?: number | null) {
  return v ? 'diff-bad' : 'diff-ok'
}

/** 异常行整行淡红底，一眼能扫出来 */
function rowClassName({ row }: { row: ReconItem }) {
  return row.recon_status && row.recon_status !== 'OK' ? 'row-abnormal' : ''
}

/** 效期展示：哨兵日期（9999-12-30）表示不管理效期 */
function fmtExpiry(d?: string) {
  if (!d || d.startsWith('9999')) return '—'
  return d
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.inventory-recon {
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

/* ---------- 汇总 + tab ---------- */
.head-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 22px;
}

.summary-item {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: v.$text-secondary;

  strong {
    font-size: 17px;
    color: v.$text-primary;
  }
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.dot-ok {
    background: #6fd39b;
  }
  &.dot-bad {
    background: #e06c6c;
  }
}

.text-bad {
  color: #e06c6c !important;
}

.summary-total {
  font-size: 12px;
  color: v.$text-muted;
  margin-left: auto;
}

.tab-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid v.$card-border;
  background: rgba(255, 255, 255, 0.03);
  color: v.$text-secondary;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    background: rgba(74, 125, 224, 0.18);
    border-color: rgba(74, 125, 224, 0.55);
    color: #cddcff;
    font-weight: 600;
  }
}

.tab-count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: v.$text-muted;
}

/* ---------- 列表 ---------- */
.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

  :deep(.row-abnormal) {
    background: rgba(224, 108, 108, 0.07);
  }
}

.loc-code {
  font-family: 'SF Mono', Consolas, monospace;
  color: #9db8ec;
}

.diff-bad {
  color: #e06c6c;
  font-weight: 700;
}

.diff-ok {
  color: v.$text-muted;
}
</style>
