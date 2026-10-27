<template>
  <div class="sku-manage">
    <!-- ============ 工具栏 ============ -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="编码 / 名称 / 条码"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="filters.category" placeholder="如：饮料" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建商品
      </el-button>
    </section>

    <!-- ============ 列表 ============ -->
    <section class="panel">
      <div class="panel-title">
        <span>商品主数据</span>
        <span class="panel-hint">编码与条码创建后不可修改（契约约束）</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无商品"
        :row-key="(r: Sku) => r.id!"
        class="data-table"
      >
        <el-table-column prop="sku_code" label="SKU 编码" min-width="120">
          <template #default="{ row }"><span class="code">{{ row.sku_code }}</span></template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="规格" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.spec || '—' }}</template>
        </el-table-column>
        <el-table-column label="分类" width="100">
          <template #default="{ row }">{{ row.category || '—' }}</template>
        </el-table-column>
        <el-table-column label="单位" width="80" align="center">
          <template #default="{ row }">{{ row.base_uom }}</template>
        </el-table-column>
        <el-table-column label="批次管理" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_batch_managed ? 'warning' : 'info'" size="small">
              {{ row.is_batch_managed ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="安全库存" width="100" align="right">
          <template #default="{ row }">{{ row.safety_stock ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <span :class="row.status === 1 ? 'status-on' : 'status-off'">
              {{ row.status === 1 ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
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
          @size-change="onSizeChange"
        />
      </div>
    </section>

    <!-- ============ 新建 / 编辑弹窗 ============ -->
    <el-dialog
      v-model="formVisible"
      :title="isEdit ? `编辑商品 · ${form.sku_code}` : '新建商品'"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-divider content-position="left">基本信息</el-divider>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="SKU 编码" prop="sku_code">
              <el-input v-model="form.sku_code" placeholder="如 SKU0001" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="条码">
              <el-input v-model="form.barcode" placeholder="条形码" :disabled="isEdit" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" placeholder="商品名称" maxlength="100" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="规格">
              <el-input v-model="form.spec" placeholder="如 550ml*24/箱" maxlength="60" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="form.category" placeholder="如 饮料" maxlength="30" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="基本单位">
              <el-input v-model="form.base_uom" placeholder="箱 / 提 / 袋" maxlength="10" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="ABC 分类">
              <el-select v-model="form.abc_class" placeholder="未设置" clearable style="width: 100%">
                <el-option label="A（高价值）" value="A" />
                <el-option label="B（中价值）" value="B" />
                <el-option label="C（低价值）" value="C" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="保质期(天)">
              <el-input-number v-model="form.shelf_life_days" :min="0" :precision="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重量(kg)">
              <el-input-number v-model="form.weight_kg" :min="0" :precision="3" :disabled="isEdit" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">库存参数</el-divider>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="批次管理">
              <el-switch v-model="form.is_batch_managed" active-text="需要" inactive-text="不需要" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="体积(m³)">
              <el-input-number v-model="form.volume_m3" :min="0" :precision="4" :disabled="isEdit" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="安全库存">
              <el-input-number v-model="form.safety_stock" :min="0" :precision="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="补货点">
              <el-input-number v-model="form.reorder_point" :min="0" :precision="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-alert
          v-if="isEdit"
          type="info"
          :closable="false"
          show-icon
          title="编码 / 条码 / 重量 / 体积创建后不可修改（契约未开放），如需更换请新建商品"
        />
      </el-form>

      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// SKU 管理：列表 / 新建 / 编辑
// - 列表：GET /skus?keyword=&category=&page=&page_size=（无 status 筛选参数）
// - 新建：POST /skus（必填 sku_code + name）
// - 编辑：PUT /skus/{id}（字段全可选）
// - 红线：PUT 不开放 sku_code / barcode / weight_kg / volume_m3 → 编辑时保持只读，
//         不做成"可编辑但保存无效"的假象
// - base_uom 是中文（箱/提/袋），早期样例有 BOX：不做单位枚举校验
// =============================================================================
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components, paths } from '@/api/schema'

type Sku = components['schemas']['Sku']
type SkuListQuery = NonNullable<paths['/skus']['get']['parameters']['query']>
type AbcClass = 'A' | 'B' | 'C'

const loading = ref(false)
const rows = ref<Sku[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({
  keyword: '',
  category: '',
})

async function loadData() {
  loading.value = true
  try {
    const query: SkuListQuery = { page: page.value, page_size: pageSize.value }
    if (filters.keyword) query.keyword = filters.keyword.trim()
    if (filters.category) query.category = filters.category.trim()

    const { data } = await client.GET('/skus', { params: { query } })
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
  filters.keyword = ''
  filters.category = ''
  page.value = 1
  loadData()
}

function onSizeChange() {
  page.value = 1
  loadData()
}

// ---------- 表单 ----------
const formVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const editingId = ref<number | null>(null)

function emptyForm() {
  return {
    sku_code: '',
    barcode: '',
    name: '',
    spec: '',
    category: '',
    base_uom: 'EA',
    weight_kg: undefined as number | undefined,
    volume_m3: undefined as number | undefined,
    shelf_life_days: undefined as number | undefined,
    abc_class: undefined as AbcClass | undefined,
    is_batch_managed: false,
    safety_stock: 0,
    reorder_point: 0,
  }
}

const form = reactive(emptyForm())

const rules: FormRules = {
  sku_code: [{ required: true, message: '请输入 SKU 编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, emptyForm())
  formVisible.value = true
}

function openEdit(row: Sku) {
  isEdit.value = true
  editingId.value = row.id ?? null
  Object.assign(form, {
    sku_code: row.sku_code ?? '',
    barcode: row.barcode ?? '',
    name: row.name ?? '',
    spec: row.spec ?? '',
    category: row.category ?? '',
    base_uom: row.base_uom ?? 'EA',
    weight_kg: row.weight_kg ?? undefined,
    volume_m3: row.volume_m3 ?? undefined,
    shelf_life_days: row.shelf_life_days ?? undefined,
    abc_class: (row.abc_class as AbcClass) ?? undefined,
    is_batch_managed: !!row.is_batch_managed,
    safety_stock: row.safety_stock ?? 0,
    reorder_point: row.reorder_point ?? 0,
  })
  formVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && editingId.value != null) {
      // PUT：只提交契约允许的字段（sku_code / barcode / weight / volume 不传）
      await client.PUT('/skus/{id}', {
        params: { path: { id: editingId.value } },
        body: {
          name: form.name,
          spec: form.spec || null,
          category: form.category || null,
          base_uom: form.base_uom,
          shelf_life_days: form.shelf_life_days ?? null,
          abc_class: form.abc_class ?? null,
          is_batch_managed: form.is_batch_managed,
          safety_stock: form.safety_stock,
          reorder_point: form.reorder_point,
        },
      })
      ElMessage.success('已保存')
    } else {
      await client.POST('/skus', {
        body: {
          sku_code: form.sku_code,
          barcode: form.barcode || null,
          name: form.name,
          spec: form.spec || null,
          category: form.category || null,
          base_uom: form.base_uom || 'EA',
          weight_kg: form.weight_kg ?? null,
          volume_m3: form.volume_m3 ?? null,
          shelf_life_days: form.shelf_life_days ?? null,
          abc_class: form.abc_class ?? null,
          is_batch_managed: form.is_batch_managed,
          safety_stock: form.safety_stock,
          reorder_point: form.reorder_point,
        },
      })
      ElMessage.success('商品已创建')
    }

    formVisible.value = false
    loadData()
  } catch (e) {
    // SKU_CODE_EXISTS（409）等错误已由 client 转中文
    ElMessage.error(e instanceof ApiError ? e.message : '保存失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.sku-manage {
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

.code {
  font-family: 'SF Mono', Consolas, monospace;
  font-weight: 600;
  color: #9db8ec;
}

.status-on {
  color: #6fd39b;
  font-size: 13px;
}

.status-off {
  color: v.$text-muted;
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
