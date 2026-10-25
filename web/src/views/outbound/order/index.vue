<template>
  <div class="outbound-order">
    <!-- ============ 工具栏 ============ -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="(s, k) in STATUS_MAP" :key="k" :label="s.text" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建出库单
      </el-button>
    </section>

    <!-- ============ 列表 ============ -->
    <section class="panel">
      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无出库单"
        :row-key="(r: OutboundOrder) => r.id!"
        class="data-table"
      >
        <el-table-column prop="order_no" label="单号" min-width="170" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ ORDER_TYPE_TEXT[row.order_type] ?? row.order_type }}</template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.customer_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="STATUS_MAP[row.status]?.tag ?? 'info'" size="small">
              {{ STATUS_MAP[row.status]?.text ?? row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90" align="center">
          <template #default="{ row }">{{ row.priority ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="总数量" width="90" align="right">
          <template #default="{ row }">{{ row.total_qty ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="要求发货" width="110">
          <template #default="{ row }">{{ row.requested_ship_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'DRAFT'"
              link
              type="warning"
              :disabled="busyId === row.id"
              @click="handleAllocate(row)"
            >
              分配
            </el-button>
            <el-button
              v-if="row.status === 'DRAFT' || row.status === 'ALLOCATED'"
              link
              type="danger"
              :disabled="busyId === row.id"
              @click="handleCancel(row)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadData"
          @size-change="onSizeChange"
        />
      </div>
    </section>

    <!-- ============ 新建弹窗 ============ -->
    <el-dialog v-model="createVisible" title="新建出库单" width="760px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单据类型" prop="order_type">
              <el-select v-model="createForm.order_type" style="width: 100%">
                <el-option label="销售出库" value="SALE" />
                <el-option label="退货出库" value="RETURN" />
                <el-option label="调拨出库" value="TRANSFER" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-input-number v-model="createForm.priority" :min="1" :max="999" :precision="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="客户">
              <el-input v-model="createForm.customer_name" placeholder="客户名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="要求发货">
              <el-date-picker
                v-model="createForm.requested_ship_at"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
        </el-form-item>

        <el-divider content-position="left">出库明细</el-divider>

        <div v-for="(line, idx) in createForm.lines" :key="idx" class="line-row">
          <span class="line-no">{{ idx + 1 }}</span>
          <el-select v-model="line.sku_id" placeholder="选择商品" filterable class="line-sku">
            <el-option v-for="s in skuOptions" :key="s.id" :label="`${s.sku_code} · ${s.name}`" :value="s.id!" />
          </el-select>
          <el-input-number v-model="line.qty_required" :min="1" :precision="0" class="line-qty" placeholder="数量" />
          <el-button link type="danger" :disabled="createForm.lines.length <= 1" @click="removeLine(idx)">删除</el-button>
        </div>

        <el-button link type="primary" class="add-line" @click="addLine">
          <el-icon><Plus /></el-icon> 添加明细
        </el-button>
      </el-form>

      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">提交</el-button>
      </template>
    </el-dialog>

    <!-- ============ 详情抽屉 ============ -->
    <el-drawer v-model="detailVisible" title="出库单详情" size="620px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="单号">{{ detail.order_no }}</el-descriptions-item>
            <el-descriptions-item label="类型">
              {{ ORDER_TYPE_TEXT[detail.order_type!] ?? detail.order_type }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="STATUS_MAP[detail.status!]?.tag ?? 'info'" size="small">
                {{ STATUS_MAP[detail.status!]?.text ?? detail.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="客户">{{ detail.customer_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="优先级">{{ detail.priority ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="要求发货">{{ detail.requested_ship_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="承运商">{{ detail.carrier || '—' }}</el-descriptions-item>
            <el-descriptions-item label="运单号">{{ detail.tracking_no || '—' }}</el-descriptions-item>
            <el-descriptions-item label="发货时间">{{ detail.shipped_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="总数量">{{ detail.total_qty ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="detail-title">明细（{{ detail.lines?.length ?? 0 }} 行）</div>
          <el-table :data="detail.lines ?? []" size="small" border>
            <el-table-column prop="line_no" label="#" width="50" />
            <el-table-column prop="sku_code" label="SKU" min-width="110" />
            <el-table-column prop="sku_name" label="名称" min-width="130" show-overflow-tooltip />
            <el-table-column label="应拣" width="80" align="right">
              <template #default="{ row }">{{ row.qty_required ?? 0 }}</template>
            </el-table-column>
            <el-table-column label="实拣" width="80" align="right">
              <template #default="{ row }">{{ row.qty_actual ?? 0 }}</template>
            </el-table-column>
            <el-table-column label="短拣" width="70" align="right">
              <template #default="{ row }">{{ row.qty_rejected ?? 0 }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">{{ LINE_STATUS_TEXT[row.status!] ?? row.status }}</template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 出库作业台（PC）：列表 O1 / 建单 O2 / 详情 O3 / 分配 O4 / 取消 O7
// - 分配必须带 Idempotency-Key（确认时生成，重试复用）
// - 分配失败 409 INVENTORY_INSUFFICIENT → 弹缺货明细（sku_code/available/shortfall）
// - 取消带 Idempotency-Key（契约 cancel_outbound_order 的 header 含 Idempotency-Key）
// =============================================================================
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { client, ApiError, makeIdempotencyKey } from '@/api/client'
import type { components, paths } from '@/api/schema'

type OutboundOrder = components['schemas']['OutboundOrder']
type OutboundOrderDetail = components['schemas']['OutboundOrderDetail']
type Sku = components['schemas']['Sku']
type OutboundListQuery = NonNullable<paths['/outbound-orders']['get']['parameters']['query']>

const STATUS_MAP: Record<string, { text: string; tag: 'primary' | 'success' | 'info' | 'warning' | 'danger' }> = {
  DRAFT: { text: '草稿', tag: 'info' },
  ALLOCATED: { text: '已分配', tag: 'warning' },
  PICKING: { text: '拣货中', tag: 'warning' },
  PICKED: { text: '已拣货', tag: 'primary' },
  SHIPPED: { text: '已发运', tag: 'success' },
  CANCELLED: { text: '已取消', tag: 'info' },
}

const ORDER_TYPE_TEXT: Record<string, string> = {
  SALE: '销售出库',
  RETURN: '退货出库',
  TRANSFER: '调拨出库',
}

const LINE_STATUS_TEXT: Record<string, string> = {
  OPEN: '待处理',
  ALLOCATED: '已分配',
  PARTIAL: '部分完成',
  DONE: '已完成',
  CANCELLED: '已取消',
}

// ---------- 列表 ----------
const loading = ref(false)
const rows = ref<OutboundOrder[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const busyId = ref<number | null>(null)

const filters = reactive({
  status: '' as NonNullable<OutboundListQuery['status']> | '',
})

async function loadData() {
  loading.value = true
  try {
    const query: OutboundListQuery = { page: page.value, page_size: pageSize.value }
    if (filters.status) query.status = filters.status

    const { data } = await client.GET('/outbound-orders', { params: { query } })
    rows.value = data?.items ?? []
    total.value = data?.meta?.total ?? 0
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载失败，请稍后重试')
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
  filters.status = ''
  page.value = 1
  loadData()
}

function onSizeChange() {
  page.value = 1
  loadData()
}

// ---------- 分配 ----------
async function handleAllocate(row: OutboundOrder) {
  try {
    await ElMessageBox.confirm(`确定对「${row.order_no}」执行库存分配？`, '确认分配', {
      type: 'info',
      confirmButtonText: '开始分配',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  busyId.value = row.id ?? null
  const key = makeIdempotencyKey(row.order_no ?? String(row.id), 'ALLOCATE')
  try {
    // 契约：allocate 必须带 Idempotency-Key
    await client.POST('/outbound-orders/{id}/allocate', {
      params: { path: { id: row.id! }, header: { 'Idempotency-Key': key } },
    })
    ElMessage.success('分配成功')
    loadData()
  } catch (e) {
    if (e instanceof ApiError && e.code === 'INVENTORY_INSUFFICIENT') {
      showShortage(e.detail)
    } else {
      ElMessage.error(e instanceof ApiError ? e.message : '分配失败，请稍后重试')
    }
  } finally {
    busyId.value = null
  }
}

/** 库存不足：展示契约 detail 里的缺货明细（sku_code / required / available / shortfall） */
function showShortage(detail: unknown) {
  const d = (detail ?? {}) as {
    sku_code?: string
    batch_no?: string
    required?: number
    available?: number
    shortfall?: number
    note?: string
  }
  const lines = [
    d.sku_code ? `商品：${d.sku_code}` : '',
    d.batch_no ? `批次：${d.batch_no}` : '',
    `需求 ${d.required ?? '—'} / 可用 ${d.available ?? '—'} / 缺 ${d.shortfall ?? '—'}`,
    d.note ? `<span class="shortage-note">${d.note}</span>` : '请拆分该明细后重试。',
  ].filter(Boolean)

  ElMessageBox.alert(lines.join('<br/>'), '可用库存不足', {
    dangerouslyUseHTMLString: true,
    type: 'warning',
    confirmButtonText: '知道了',
  })
}

// ---------- 取消 ----------
async function handleCancel(row: OutboundOrder) {
  try {
    await ElMessageBox.confirm(`确定取消出库单「${row.order_no}」？取消后不可恢复。`, '确认取消', {
      type: 'warning',
      confirmButtonText: '确认取消',
      cancelButtonText: '再想想',
    })
  } catch {
    return
  }

  busyId.value = row.id ?? null
  const key = makeIdempotencyKey(row.order_no ?? String(row.id), 'CANCEL')
  try {
    // 契约：cancel_outbound_order 的 header 含 Idempotency-Key
    await client.POST('/outbound-orders/{id}/cancel', {
      params: { path: { id: row.id! }, header: { 'Idempotency-Key': key } },
    })
    ElMessage.success('已取消')
    loadData()
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '取消失败，请稍后重试')
  } finally {
    busyId.value = null
  }
}

// ---------- 新建 ----------
const createVisible = ref(false)
const submitting = ref(false)
const createFormRef = ref<FormInstance>()
const skuOptions = ref<Sku[]>([])

const createForm = reactive({
  order_type: 'SALE' as NonNullable<components['schemas']['OutboundOrderCreate']['order_type']>,
  customer_name: '',
  priority: 100,
  requested_ship_at: '' as string | null,
  remark: '',
  lines: [{ sku_id: undefined as number | undefined, qty_required: 1 }],
})

const createRules: FormRules = {
  order_type: [{ required: true, message: '请选择单据类型', trigger: 'change' }],
}

async function openCreate() {
  createVisible.value = true
  if (!skuOptions.value.length) {
    try {
      const { data } = await client.GET('/skus', { params: { query: { page: 1, page_size: 100 } } })
      skuOptions.value = data?.items ?? []
    } catch (e) {
      ElMessage.error(e instanceof ApiError ? e.message : '加载商品失败')
    }
  }
}

function addLine() {
  createForm.lines.push({ sku_id: undefined, qty_required: 1 })
}

function removeLine(idx: number) {
  if (createForm.lines.length > 1) createForm.lines.splice(idx, 1)
}

function validateLines(): string | null {
  if (!createForm.lines.length) return '至少需要一行明细'
  for (let i = 0; i < createForm.lines.length; i++) {
    const l = createForm.lines[i]
    if (!l.sku_id) return `第 ${i + 1} 行未选择商品`
    if (!l.qty_required || l.qty_required <= 0) return `第 ${i + 1} 行数量必须大于 0`
  }
  return null
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  const lineErr = validateLines()
  if (lineErr) {
    ElMessage.warning(lineErr)
    return
  }

  submitting.value = true
  try {
    await client.POST('/outbound-orders', {
      body: {
        order_type: createForm.order_type,
        customer_name: createForm.customer_name || null,
        priority: createForm.priority,
        requested_ship_at: createForm.requested_ship_at || null,
        remark: createForm.remark || null,
        lines: createForm.lines.map((l) => ({ sku_id: l.sku_id!, qty_required: l.qty_required })),
      },
    })
    ElMessage.success('出库单已创建')
    createVisible.value = false
    resetCreateForm()
    page.value = 1
    loadData()
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '创建失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

function resetCreateForm() {
  createForm.order_type = 'SALE'
  createForm.customer_name = ''
  createForm.priority = 100
  createForm.requested_ship_at = ''
  createForm.remark = ''
  createForm.lines = [{ sku_id: undefined, qty_required: 1 }]
}

// ---------- 详情 ----------
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<OutboundOrderDetail | null>(null)

async function openDetail(row: OutboundOrder) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const { data } = await client.GET('/outbound-orders/{id}', { params: { path: { id: row.id! } } })
    detail.value = data ?? null
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载详情失败')
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.outbound-order {
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

.toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
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

.data-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.03);
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-text-color: #{v.$text-primary};
  --el-table-header-text-color: #{v.$text-secondary};
  --el-table-row-hover-bg-color: rgba(74, 125, 224, 0.1);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.line-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.line-no {
  width: 20px;
  color: v.$text-muted;
  font-size: 12px;
}

.line-sku {
  flex: 1;
}

.line-qty {
  width: 130px;
}

.add-line {
  margin-left: 30px;
}

.detail-body {
  min-height: 200px;
}

.detail-title {
  margin: 20px 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;
}

:deep(.shortage-note) {
  color: #f0a75a;
}
</style>
