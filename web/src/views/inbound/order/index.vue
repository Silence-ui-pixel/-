<template>
  <div class="inbound-order">
    <!-- ============ 工具栏 ============ -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 140px">
            <el-option v-for="(s, k) in STATUS_MAP" :key="k" :label="s.text" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="单据类型">
          <el-select v-model="filters.order_type" placeholder="全部" clearable style="width: 140px">
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

      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建入库单
      </el-button>
    </section>

    <!-- ============ 列表 ============ -->
    <section class="panel">
      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无入库单"
        :row-key="(r: InboundOrder) => r.id!"
        class="data-table"
      >
        <el-table-column prop="order_no" label="单号" min-width="170" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ ORDER_TYPE_TEXT[row.order_type] ?? row.order_type }}</template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.supplier_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="STATUS_MAP[row.status]?.tag ?? 'info'" size="small">
              {{ STATUS_MAP[row.status]?.text ?? row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预计到货" width="110">
          <template #default="{ row }">{{ row.expected_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="应收 / 实收" width="130" align="right">
          <template #default="{ row }">
            <span class="qty-text">{{ row.total_expected_qty ?? 0 }}</span>
            <span class="qty-sep">/</span>
            <span class="qty-received">{{ row.total_received_qty ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'DRAFT'"
              link
              type="danger"
              :disabled="cancellingId === row.id"
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
    <el-dialog v-model="createVisible" title="新建入库单" width="760px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单据类型" prop="order_type">
              <el-select v-model="createForm.order_type" style="width: 100%">
                <el-option label="采购入库" value="PO" />
                <el-option label="退货入库" value="RETURN" />
                <el-option label="调拨入库" value="TRANSFER" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预计到货">
              <el-date-picker
                v-model="createForm.expected_at"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="供应商">
          <el-input v-model="createForm.supplier_name" placeholder="供应商名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" maxlength="200" show-word-limit />
        </el-form-item>

        <el-divider content-position="left">入库明细</el-divider>

        <div v-for="(line, idx) in createForm.lines" :key="idx" class="line-row">
          <span class="line-no">{{ idx + 1 }}</span>
          <el-select
            v-model="line.sku_id"
            placeholder="选择商品"
            filterable
            class="line-sku"
          >
            <el-option
              v-for="s in skuOptions"
              :key="s.id"
              :label="`${s.sku_code} · ${s.name}`"
              :value="s.id!"
            />
          </el-select>
          <el-input-number v-model="line.qty_required" :min="1" :precision="0" class="line-qty" placeholder="数量" />
          <el-button link type="danger" :disabled="createForm.lines.length <= 1" @click="removeLine(idx)">
            删除
          </el-button>
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
    <el-drawer v-model="detailVisible" title="入库单详情" size="620px">
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
            <el-descriptions-item label="供应商">{{ detail.supplier_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="预计到货">{{ detail.expected_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="收货时间">{{ detail.received_at || '—' }}</el-descriptions-item>
            <el-descriptions-item label="应收总量">{{ detail.total_expected_qty ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="实收总量">{{ detail.total_received_qty ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="detail-title">明细（{{ detail.lines?.length ?? 0 }} 行）</div>
          <el-table :data="detail.lines ?? []" size="small" border>
            <el-table-column prop="line_no" label="#" width="50" />
            <el-table-column prop="sku_code" label="SKU" min-width="110" />
            <el-table-column prop="sku_name" label="名称" min-width="130" show-overflow-tooltip />
            <el-table-column label="应收" width="80" align="right">
              <template #default="{ row }">{{ row.qty_required ?? 0 }}</template>
            </el-table-column>
            <el-table-column label="实收" width="80" align="right">
              <template #default="{ row }">{{ row.qty_actual ?? 0 }}</template>
            </el-table-column>
            <el-table-column label="不良" width="70" align="right">
              <template #default="{ row }">{{ row.qty_rejected ?? 0 }}</template>
            </el-table-column>
            <el-table-column label="批次" min-width="110">
              <template #default="{ row }">{{ row.batch_no || '—' }}</template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 入库作业台（PC）：列表 B1 / 建单 B2 / 详情 B3 / 取消 B7
// - 类型全部来自契约（components / paths），无手写业务 interface
// - 契约冻结规则：只增不改；状态机 DRAFT→RECEIVED→PUTAWAY→DONE
// - 入库取消（B7）的 header 是 never（契约限制），因此不传 Idempotency-Key
// - 建单不做幂等（契约约定），用按钮 loading 防抖
// =============================================================================
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components, paths } from '@/api/schema'

type InboundOrder = components['schemas']['InboundOrder']
type InboundOrderDetail = components['schemas']['InboundOrderDetail']
type Sku = components['schemas']['Sku']
type InboundListQuery = NonNullable<paths['/inbound-orders']['get']['parameters']['query']>

/** 状态展示映射（与契约状态机一致） */
const STATUS_MAP: Record<string, { text: string; tag: 'primary' | 'success' | 'info' | 'warning' | 'danger' }> = {
  DRAFT: { text: '草稿', tag: 'info' },
  ARRIVED: { text: '已到货', tag: 'warning' },
  RECEIVING: { text: '收货中', tag: 'warning' },
  RECEIVED: { text: '已收货', tag: 'primary' },
  PUTAWAY: { text: '已上架', tag: 'success' },
  DONE: { text: '已完成', tag: 'success' },
  CANCELLED: { text: '已取消', tag: 'info' },
}

const ORDER_TYPE_TEXT: Record<string, string> = {
  PO: '采购入库',
  RETURN: '退货入库',
  TRANSFER: '调拨入库',
}

// ---------- 列表 ----------
const loading = ref(false)
const rows = ref<InboundOrder[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const cancellingId = ref<number | null>(null)

const filters = reactive({
  status: '' as NonNullable<InboundListQuery['status']> | '',
  order_type: '' as NonNullable<InboundListQuery['order_type']> | '',
})

async function loadData() {
  loading.value = true
  try {
    const query: InboundListQuery = { page: page.value, page_size: pageSize.value }
    if (filters.status) query.status = filters.status
    if (filters.order_type) query.order_type = filters.order_type

    const { data } = await client.GET('/inbound-orders', { params: { query } })
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
  filters.order_type = ''
  page.value = 1
  loadData()
}

function onSizeChange() {
  page.value = 1
  loadData()
}

// ---------- 取消 ----------
async function handleCancel(row: InboundOrder) {
  try {
    await ElMessageBox.confirm(`确定取消入库单「${row.order_no}」？取消后不可恢复。`, '确认取消', {
      type: 'warning',
      confirmButtonText: '确认取消',
      cancelButtonText: '再想想',
    })
  } catch {
    return // 用户点了"再想想"
  }

  cancellingId.value = row.id ?? null
  try {
    // 契约：cancel_inbound_order 的 header 为 never，不传 Idempotency-Key
    await client.POST('/inbound-orders/{id}/cancel', { params: { path: { id: row.id! } } })
    ElMessage.success('已取消')
    loadData()
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '取消失败，请稍后重试')
  } finally {
    cancellingId.value = null
  }
}

// ---------- 新建 ----------
const createVisible = ref(false)
const submitting = ref(false)
const createFormRef = ref<FormInstance>()
const skuOptions = ref<Sku[]>([])

const createForm = reactive({
  order_type: 'PO' as NonNullable<components['schemas']['InboundOrderCreate']['order_type']>,
  supplier_name: '',
  expected_at: '' as string | null,
  remark: '',
  lines: [{ sku_id: undefined as number | undefined, qty_required: 1 }],
})

const createRules: FormRules = {
  order_type: [{ required: true, message: '请选择单据类型', trigger: 'change' }],
}

/** 打开新建弹窗：首次加载 SKU 选项 */
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

/** 前端预校验（后端仍会 422 兜底） */
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
    // 契约：建单不做幂等，按钮 loading 防抖即可
    await client.POST('/inbound-orders', {
      body: {
        order_type: createForm.order_type,
        supplier_name: createForm.supplier_name || null,
        expected_at: createForm.expected_at || null,
        remark: createForm.remark || null,
        lines: createForm.lines.map((l) => ({ sku_id: l.sku_id!, qty_required: l.qty_required })),
      },
    })
    ElMessage.success('入库单已创建')
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
  createForm.order_type = 'PO'
  createForm.supplier_name = ''
  createForm.expected_at = ''
  createForm.remark = ''
  createForm.lines = [{ sku_id: undefined, qty_required: 1 }]
}

// ---------- 详情 ----------
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<InboundOrderDetail | null>(null)

async function openDetail(row: InboundOrder) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const { data } = await client.GET('/inbound-orders/{id}', { params: { path: { id: row.id! } } })
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

.inbound-order {
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

.qty-text {
  color: v.$text-primary;
}
.qty-sep {
  margin: 0 4px;
  color: v.$text-muted;
}
.qty-received {
  color: #6fd39b;
  font-weight: 600;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* ---------- 新建弹窗明细行 ---------- */
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

/* ---------- 详情抽屉 ---------- */
.detail-body {
  min-height: 200px;
}

.detail-title {
  margin: 20px 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;
}
</style>
