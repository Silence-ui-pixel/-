<template>
  <div class="pda-inventory">
    <!-- 顶部：仅保留条码输入 + 查询（无任何筛选按钮） -->
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="扫描 / 输入 SKU 条码"
        size="large"
        clearable
        :disabled="loading"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" size="large" :loading="loading" @click="handleSearch">查询</el-button>
    </div>

    <!-- 状态提示 -->
    <div v-if="loading" class="state-hint">查询中…</div>
    <div v-else-if="!rows.length" class="state-hint">
      {{ searched ? '未找到该商品的库存' : '扫描或输入条码后查询' }}
    </div>

    <!-- 精简结果列表（纯只读） -->
    <ul v-else class="result-list">
      <li v-for="(row, idx) in rows" :key="idx" class="result-item">
        <div class="item-head">
          <span class="item-name">{{ row.sku_name || row.sku_code }}</span>
          <span class="item-code">{{ row.sku_code }}</span>
        </div>
        <div class="item-meta">
          <span>库位 {{ row.location_code || '—' }}</span>
          <span v-if="row.batch_no">批次 {{ row.batch_no }}</span>
          <span v-if="row.location_type">{{ locationTypeText(row.location_type) }}</span>
        </div>
        <div class="item-qty">
          <span class="qty-label">可用库存</span>
          <span class="qty-value">{{ row.qty_available ?? 0 }}</span>
          <span class="qty-unit">{{ row.base_uom || '' }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// PDA 库存速查（只读）
// - 交互：仅扫/输条码 → 查询；无筛选、无任何写操作
// - 数据：client.GET('/inventory')，类型来自契约 schema.d.ts
// - 错误：client 统一转 ApiError（中文 message），此处 catch 弹提示
// =============================================================================
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components } from '@/api/schema'

type InventoryRow = components['schemas']['InventoryItem']

const keyword = ref('')
const loading = ref(false)
const searched = ref(false)
const rows = ref<InventoryRow[]>([])

async function handleSearch() {
  const kw = keyword.value.trim()
  if (!kw) {
    rows.value = []
    searched.value = false
    return
  }

  loading.value = true
  try {
    // 条码同时按 sku_code / barcode 匹配（mock 侧宽松处理，真实后端以契约为准）
    const { data } = await client.GET('/inventory', {
      params: { query: { sku_code: kw, only_available: true } },
    })
    rows.value = data?.items ?? []
    searched.value = true
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '查询失败，请稍后重试')
    rows.value = []
    searched.value = true
  } finally {
    loading.value = false
  }
}

/** 库位类型中文映射（仅展示用） */
function locationTypeText(t: string) {
  const map: Record<string, string> = {
    STORAGE: '存储位',
    RECEIVING: '收货暂存',
    PICKING: '拣货位',
    STAGING: '发货暂存',
    QUARANTINE: '隔离待检',
  }
  return map[t] ?? t
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.pda-inventory {
  padding: 16px 14px 28px;
}

/* ---------- 搜索栏 ---------- */
.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    box-shadow: 0 0 0 1px v.$card-border inset;
  }
  :deep(.el-input__inner) {
    color: v.$text-primary;
    font-size: 16px; /* 手持端可读性 */
  }
}

/* ---------- 状态提示 ---------- */
.state-hint {
  margin-top: 40px;
  text-align: center;
  font-size: 14px;
  color: v.$text-muted;
}

/* ---------- 结果列表 ---------- */
.result-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  padding: 14px;
  border-radius: 12px;
  background: rgba(24, 29, 42, 0.78);
  border: 1px solid v.$card-border;
}

.item-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.item-name {
  font-size: 16px;
  font-weight: 600;
  color: v.$text-primary;
}

.item-code {
  font-size: 12px;
  color: v.$text-muted;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
  font-size: 12px;
  color: v.$text-secondary;
}

.item-qty {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(255, 255, 255, 0.07);
}

.qty-label {
  font-size: 13px;
  color: v.$text-secondary;
}

.qty-value {
  font-size: 22px;
  font-weight: 700;
  color: #6fd39b;
  line-height: 1;
}

.qty-unit {
  font-size: 12px;
  color: v.$text-muted;
}
</style>
