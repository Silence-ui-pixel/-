<template>
  <div class="inventory-query">
    <!-- ============ 筛选区 ============ -->
    <section class="panel filter-panel">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="SKU 编码">
          <el-input v-model="filters.sku_code" placeholder="编码 / 名称" clearable :disabled="loading" />
        </el-form-item>

        <el-form-item label="库位 / 库区">
          <el-input v-model="filters.location_code" placeholder="如 WH01-A 或 WH01-A-01-01" clearable :disabled="loading" />
        </el-form-item>

        <el-form-item label="库位类型">
          <el-select v-model="filters.location_type" placeholder="全部" clearable :disabled="loading" style="width: 150px">
            <el-option label="存储位" value="STORAGE" />
            <el-option label="收货暂存" value="RECEIVING" />
            <el-option label="拣货位" value="PICKING" />
            <el-option label="发货暂存" value="STAGING" />
            <el-option label="隔离待检" value="QUARANTINE" />
          </el-select>
        </el-form-item>

        <el-form-item label="批次">
          <el-input v-model="filters.batch_no" placeholder="批次号" clearable :disabled="loading" style="width: 150px" />
        </el-form-item>

        <el-form-item label="效期预警">
          <el-input-number v-model="filters.expiring_days" :min="1" :max="3650" placeholder="天数" :disabled="loading" controls-position="right" style="width: 120px" />
          <span class="unit-text">天内到期</span>
        </el-form-item>

        <el-form-item label="只看有货">
          <el-switch v-model="filters.only_available" :disabled="loading" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button :disabled="loading" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <!-- ============ 列表区 ============ -->
    <section class="panel table-panel">
      <div class="panel-title">
        <span>库存明细</span>
        <span class="panel-count">共 {{ total }} 条</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无库存数据"
        :row-key="rowKey"
        class="inv-table"
        @row-click="handleRowClick"
      >
        <el-table-column prop="sku_code" label="SKU 编码" min-width="120" />
        <el-table-column prop="sku_name" label="商品名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="规格" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '—' }}</template>
        </el-table-column>
        <el-table-column prop="location_code" label="库位全码" min-width="130" />
        <el-table-column label="批次" min-width="110">
          <template #default="{ row }">{{ row.batch_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="效期" min-width="110">
          <template #default="{ row }">{{ fmtExpiry(row.expiry_date) }}</template>
        </el-table-column>
        <el-table-column label="现有库存" min-width="100" align="right">
          <template #default="{ row }">{{ row.qty_on_hand ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="已分配" min-width="90" align="right">
          <template #default="{ row }">{{ row.qty_allocated ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="可用库存" min-width="100" align="right">
          <template #default="{ row }">
            <span class="qty-available">{{ row.qty_available ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="base_uom" label="单位" width="80" align="center" />
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadData"
          @size-change="handleSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 库存查询页（PC）
// - 数据源：client.GET('/inventory')，类型全部来自契约（schema.d.ts），无手写业务 interface
// - 错误：client 已统一把非 2xx 转 ApiError（中文 message），此处 catch 后弹 ElMessage
// - 调试：页面 URL 加 ?_err=<ERROR_CODE> 可触发 mock 的错误码，验证弹窗
// =============================================================================
import { reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components, paths } from '@/api/schema'

/** 契约推导：库存查询 query 参数 & 列表行类型（全部复用契约，不手写） */
type InventoryQuery = NonNullable<paths['/inventory']['get']['parameters']['query']>
type InventoryRow = components['schemas']['InventoryItem']

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const rows = ref<InventoryRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

/** 筛选表单状态（UI 状态，非业务模型） */
const filters = reactive({
  sku_code: '',
  location_code: '',
  location_type: '' as InventoryQuery['location_type'] | '',
  batch_no: '',
  expiring_days: undefined as number | undefined,
  only_available: false,
})

/** 组装查询参数：只带非空项，避免把空串发给后端 */
function buildQuery(): InventoryQuery & { _err?: string } {
  const q: InventoryQuery & { _err?: string } = { page: page.value, page_size: pageSize.value }
  if (filters.sku_code) q.sku_code = filters.sku_code.trim()
  if (filters.location_code) q.location_code = filters.location_code.trim()
  if (filters.location_type) q.location_type = filters.location_type
  if (filters.batch_no) q.batch_no = filters.batch_no.trim()
  if (typeof filters.expiring_days === 'number') q.expiring_days = filters.expiring_days
  if (filters.only_available) q.only_available = true
  // 调试用：页面 URL 的 _err 透传给 mock，触发对应错误码
  const errCode = route.query._err
  if (typeof errCode === 'string' && errCode) q._err = errCode
  return q
}

/** 拉取库存列表 */
async function loadData() {
  loading.value = true
  try {
    const { data } = await client.GET('/inventory', { params: { query: buildQuery() } })
    rows.value = data?.items ?? []
    total.value = data?.meta?.total ?? 0
  } catch (e) {
    // client 已把后端错误转成 ApiError，message 即中文弹窗文案
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
  filters.location_code = ''
  filters.location_type = ''
  filters.batch_no = ''
  filters.expiring_days = undefined
  filters.only_available = false
  page.value = 1
  loadData()
}

function handleSizeChange() {
  page.value = 1
  loadData()
}

/** 行点击 → 跳库存流水（按该维度的 SKU 过滤） */
function handleRowClick(row: InventoryRow) {
  router.push({ path: '/inventory/txn', query: { sku_code: row.sku_code } })
}

/** 行唯一键（同一 SKU 可能分布在多个库位/批次） */
function rowKey(row: InventoryRow) {
  return `${row.sku_id}-${row.location_id}-${row.batch_no}`
}

/** 效期展示：哨兵日期 9999-12-31 表示不管理效期 */
function fmtExpiry(d?: string) {
  if (!d || d.startsWith('9999')) return '—'
  return d
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.inventory-query {
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

/* ---------- 筛选区 ---------- */
.filter-form {
  :deep(.el-form-item) {
    margin-bottom: 12px;
    margin-right: 18px;
  }
  :deep(.el-form-item__label) {
    color: v.$text-secondary;
  }
}

.unit-text {
  margin-left: 6px;
  font-size: 12px;
  color: v.$text-muted;
}

/* ---------- 列表区 ---------- */
.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;

  .panel-count {
    font-size: 12px;
    font-weight: 400;
    color: v.$text-muted;
  }
}

.inv-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.03);
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-text-color: #{v.$text-primary};
  --el-table-header-text-color: #{v.$text-secondary};
  --el-table-row-hover-bg-color: rgba(74, 125, 224, 0.1);

  :deep(.el-table__row) {
    cursor: pointer;
  }
}

/* 可用库存：主列强调 */
.qty-available {
  color: #6fd39b;
  font-weight: 600;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
