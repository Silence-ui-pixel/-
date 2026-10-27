<template>
  <div class="location-manage">
    <!-- ========== 统计条 ========== -->
    <section class="panel stats">
      <div class="stat-total">
        <span class="stat-num">{{ rows.length }}</span>
        <span class="stat-label">个库位</span>
      </div>
      <div v-for="s in stats" :key="s.type" class="stat-item">
        <span class="stat-dot" :class="`dot-${s.tag}`"></span>
        <span class="stat-text">{{ s.label }} {{ s.count }}</span>
      </div>
    </section>

    <!-- ========== 筛选 ========== -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="loadData">
        <el-form-item label="库区">
          <el-select v-model="filters.zone_code" placeholder="全部" clearable style="width: 110px">
            <el-option v-for="z in zoneOptions" :key="z" :label="`${z} 区`" :value="z" />
          </el-select>
        </el-form-item>
        <el-form-item label="库位类型">
          <el-select v-model="filters.location_type" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="(t, k) in LOCATION_TYPE_TEXT" :key="k" :label="t" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadData">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <!-- ========== 列表 ========== -->
    <section class="panel">
      <div class="panel-title">
        <span>库位列表</span>
        <span class="panel-hint">本期只读 · 契约未开放库位增删改</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无库位"
        :row-key="(r: Location) => r.id!"
        class="data-table"
      >
        <el-table-column prop="location_code" label="库位编码" min-width="110">
          <template #default="{ row }">
            <span class="loc-code">{{ row.location_code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="库区" width="80" align="center">
          <template #default="{ row }">{{ row.zone_code }}</template>
        </el-table-column>
        <el-table-column label="货架" width="80" align="center">
          <template #default="{ row }">{{ row.rack_code }}</template>
        </el-table-column>
        <el-table-column label="层" width="70" align="center">
          <template #default="{ row }">{{ row.level_no }}</template>
        </el-table-column>
        <el-table-column label="位" width="100" align="center">
          <template #default="{ row }">{{ row.bin_code }}</template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="LOCATION_TYPE_TAG[row.location_type!] ?? 'info'" size="small">
              {{ LOCATION_TYPE_TEXT[row.location_type!] ?? row.location_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="拣货顺序" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.pick_seq != null" class="pick-seq">{{ row.pick_seq }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span :class="row.status === 1 ? 'status-on' : 'status-off'">
              {{ row.status === 1 ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 库位管理（只读）
// - 接口：GET /locations（无分页，13 条一次全返回；page_size 会被忽略）
// - 筛选：zone_code / location_type / status
// - 契约未开放库位增删改，页面不提供任何编辑入口
// - 注意：location_code 现等于 bin_code（v1.3 统一），不要自己拼 warehouse-zone-rack-level-bin
// =============================================================================
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components, paths } from '@/api/schema'

type Location = components['schemas']['Location']
type LocationQuery = NonNullable<paths['/locations']['get']['parameters']['query']>

const LOCATION_TYPE_TEXT: Record<string, string> = {
  STORAGE: '存储位',
  RECEIVING: '收货暂存',
  PICKING: '拣货位',
  STAGING: '发货暂存',
  QUARANTINE: '隔离待检',
}

const LOCATION_TYPE_TAG: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  STORAGE: 'primary',
  RECEIVING: 'warning',
  PICKING: 'success',
  STAGING: 'warning',
  QUARANTINE: 'danger',
}

const loading = ref(false)
const rows = ref<Location[]>([])
const zoneOptions = ['A', 'B', 'C', 'D']

const filters = reactive({
  zone_code: '',
  location_type: '' as NonNullable<LocationQuery['location_type']> | '',
  status: undefined as 0 | 1 | undefined,
})

/** 按类型汇总（基于当前结果） */
const stats = computed(() => {
  const map = new Map<string, number>()
  for (const r of rows.value) {
    const t = r.location_type ?? 'UNKNOWN'
    map.set(t, (map.get(t) ?? 0) + 1)
  }
  return Array.from(map.entries()).map(([type, count]) => ({
    type,
    count,
    label: LOCATION_TYPE_TEXT[type] ?? type,
    tag: LOCATION_TYPE_TAG[type] ?? 'info',
  }))
})

async function loadData() {
  loading.value = true
  try {
    const query: LocationQuery = {}
    if (filters.zone_code) query.zone_code = filters.zone_code
    if (filters.location_type) query.location_type = filters.location_type
    if (filters.status !== undefined) query.status = filters.status

    const { data } = await client.GET('/locations', { params: { query } })
    rows.value = data?.items ?? []
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载失败，请稍后重试')
    rows.value = []
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filters.zone_code = ''
  filters.location_type = ''
  filters.status = undefined
  loadData()
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.location-manage {
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
  gap: 22px;
}

.stat-total {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding-right: 20px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: v.$text-primary;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: v.$text-muted;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 7px;
}

.stat-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;

  &.dot-primary { background: #4a7de0; }
  &.dot-warning { background: #f0a75a; }
  &.dot-success { background: #6fd39b; }
  &.dot-danger { background: #e06c6c; }
  &.dot-info { background: #8a94a8; }
}

.stat-text {
  font-size: 13px;
  color: v.$text-secondary;
}

/* ---------- 筛选 ---------- */
.filter-form {
  :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 16px;
  }
  :deep(.el-form-item__label) {
    color: v.$text-secondary;
  }
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
}

.loc-code {
  font-family: 'SF Mono', Consolas, monospace;
  font-weight: 600;
  color: #9db8ec;
  letter-spacing: 0.3px;
}

.pick-seq {
  color: v.$text-secondary;
}

.text-muted {
  color: v.$text-muted;
}

.status-on {
  color: #6fd39b;
  font-size: 13px;
}

.status-off {
  color: v.$text-muted;
  font-size: 13px;
}
</style>
