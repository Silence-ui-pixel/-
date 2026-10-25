<script setup lang="ts">
// =============================================================================
// PDA 扫码作业原型（H5）
// DoD：手机浏览器可用 / 扫码框自动聚焦 / 软键盘不遮输入区
// -----------------------------------------------------------------------------
// 三种模式（只做扫码识别与展示的原型，不落真实单据）：
//   收货 receive  → 扫 SKU 条码 → 查该商品在库情况
//   上架 putaway  → 扫库位码   → 查该库位存放情况
//   拣货 pick     → 扫 SKU 条码 → 查可拣库存
// 数据：复用 /inventory 接口（按 sku_code 或 location_code 查），类型全部来自契约。
// =============================================================================
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElInput } from 'element-plus'
import { client, ApiError } from '@/api/client'
import type { components } from '@/api/schema'

type InventoryRow = components['schemas']['InventoryItem']
type Mode = 'receive' | 'putaway' | 'pick'

const modes: { value: Mode; label: string; placeholder: string; tip: string }[] = [
  { value: 'receive', label: '收货', placeholder: '扫 SKU 条码', tip: '扫描供应商商品条码，核对应收数量' },
  { value: 'putaway', label: '上架', placeholder: '扫目标库位码', tip: '扫描库位条码，确认上架位置' },
  { value: 'pick', label: '拣货', placeholder: '扫 SKU 条码', tip: '扫描待拣商品条码，核对可用库存' },
]

const mode = ref<Mode>('receive')
const code = ref('')
const loading = ref(false)
const scanned = ref(false)
const rows = ref<InventoryRow[]>([])

const inputRef = ref<InstanceType<typeof ElInput>>()
const inputBarRef = ref<HTMLElement>()

const currentMode = computed(() => modes.find((m) => m.value === mode.value)!)

/** 需求提示（未扫码时展示） */
const hint = computed(() => (scanned.value ? '未找到匹配的库存记录' : currentMode.value.tip))

/** 切换模式：清空上次扫码结果，重新聚焦 */
async function switchMode(m: Mode) {
  if (mode.value === m) return
  mode.value = m
  code.value = ''
  rows.value = []
  scanned.value = false
  await focusInput()
}

/** 聚焦扫码框（移动端软键盘弹出后确保输入区可见） */
async function focusInput() {
  await nextTick()
  inputRef.value?.focus()
  // 软键盘弹出后兜底再次滚到顶部，避免遮挡输入区
  setTimeout(() => inputBarRef.value?.scrollIntoView({ block: 'start', behavior: 'smooth' }), 260)
}

/** 扫码/回车查询 */
async function handleScan() {
  const kw = code.value.trim()
  if (!kw) {
    ElMessage.warning('请先扫码或输入编码')
    return
  }

  loading.value = true
  try {
    // 上架模式按库位查，其余按商品查
    const query = mode.value === 'putaway' ? { location_code: kw } : { sku_code: kw }
    const { data } = await client.GET('/inventory', { params: { query } })
    rows.value = data?.items ?? []
    scanned.value = true
    if (!rows.value.length) ElMessage.info('未找到匹配记录')
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '识别失败，请稍后重试')
    rows.value = []
    scanned.value = true
  } finally {
    loading.value = false
    // 扫码枪回车后保持聚焦，方便连续扫码
    focusInput()
  }
}

/** 原型用：无真实扫码硬件时，点一下填入示例码并触发查询 */
function simulateScan(sample: string) {
  code.value = sample
  handleScan()
}

/** 按模式给不同的示例码 */
const samples = computed(() => (mode.value === 'putaway' ? ['WH01-A-01-01', 'WH01-R-00-01'] : ['690000000001', 'SKU-1002']))

function fmtExpiry(d?: string) {
  if (!d || d.startsWith('9999')) return '—'
  return d
}

function locationTypeText(t?: string) {
  const map: Record<string, string> = {
    STORAGE: '存储位',
    RECEIVING: '收货暂存',
    PICKING: '拣货位',
    STAGING: '发货暂存',
    QUARANTINE: '隔离待检',
  }
  return t ? map[t] ?? t : '—'
}

onMounted(focusInput)
</script>

<template>
  <div class="pda-scan">
    <!-- 模式切换 -->
    <div class="mode-bar">
      <button
        v-for="m in modes"
        :key="m.value"
        type="button"
        class="mode-btn"
        :class="{ active: mode === m.value }"
        @click="switchMode(m.value)"
      >
        {{ m.label }}
      </button>
    </div>

    <!-- 扫码输入区（固定在上方，避免软键盘遮挡） -->
    <div ref="inputBarRef" class="scan-bar">
      <el-input
        ref="inputRef"
        v-model="code"
        size="large"
        :placeholder="currentMode.placeholder"
        clearable
        :disabled="loading"
        @keyup.enter="handleScan"
        @focus="focusInput"
      >
        <template #prefix>
          <el-icon><Aim /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" size="large" :loading="loading" @click="handleScan">识别</el-button>
    </div>

    <!-- 模拟扫码（原型用） -->
    <div class="simulate-bar">
      <span class="simulate-label">模拟扫码：</span>
      <button v-for="s in samples" :key="s" type="button" class="simulate-chip" @click="simulateScan(s)">{{ s }}</button>
    </div>

    <!-- 结果区（可滚动） -->
    <div class="result-area">
      <div v-if="loading" class="state-hint">识别中…</div>
      <div v-else-if="!rows.length" class="state-hint">{{ hint }}</div>

      <ul v-else class="result-list">
        <li v-for="(row, idx) in rows" :key="idx" class="result-item">
          <div class="item-head">
            <span class="item-name">{{ row.sku_name || row.sku_code }}</span>
            <span class="item-code">{{ row.sku_code }}</span>
          </div>
          <div class="item-meta">
            <span>库位 {{ row.location_code || '—' }}</span>
            <span>{{ locationTypeText(row.location_type) }}</span>
            <span v-if="row.batch_no">批次 {{ row.batch_no }}</span>
            <span>效期 {{ fmtExpiry(row.expiry_date) }}</span>
          </div>
          <div class="item-qty">
            <span class="qty-label">可用库存</span>
            <span class="qty-value">{{ row.qty_available ?? 0 }}</span>
            <span class="qty-unit">{{ row.base_uom || '' }}</span>
          </div>

          <!-- 模式相关的下一步提示（原型只展示，不落单） -->
          <div class="item-action">
            <template v-if="mode === 'receive'">→ 下一步：输入实收数量并确认收货（待接单号）</template>
            <template v-else-if="mode === 'putaway'">→ 下一步：确认上架到该库位（待接单号）</template>
            <template v-else>→ 下一步：输入实拣数量并确认（待接单号）</template>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.pda-scan {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 12px 14px 0;
  box-sizing: border-box;
}

/* ---------- 模式切换 ---------- */
.mode-bar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  margin-bottom: 12px;
}

.mode-btn {
  flex: 1;
  height: 40px;
  border-radius: 10px;
  border: 1px solid v.$card-border;
  background: rgba(255, 255, 255, 0.04);
  color: v.$text-secondary;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    background: rgba(74, 125, 224, 0.18);
    border-color: rgba(74, 125, 224, 0.55);
    color: #cddcff;
    font-weight: 600;
  }
}

/* ---------- 扫码输入 ---------- */
.scan-bar {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  scroll-margin-top: 8px;

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    box-shadow: 0 0 0 1px v.$card-border inset;
  }
  :deep(.el-input__inner) {
    color: v.$text-primary;
    font-size: 16px;
  }
}

/* ---------- 模拟扫码 ---------- */
.simulate-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
  margin: 10px 0 4px;
  font-size: 12px;
  color: v.$text-muted;
}

.simulate-chip {
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px dashed rgba(255, 255, 255, 0.16);
  background: transparent;
  color: v.$text-secondary;
  font-size: 12px;
  cursor: pointer;

  &:active {
    background: rgba(255, 255, 255, 0.08);
  }
}

/* ---------- 结果区 ---------- */
.result-area {
  flex: 1;
  min-height: 0; /* flex 子项滚动修复 */
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 10px 0 24px;
}

.state-hint {
  margin-top: 40px;
  text-align: center;
  font-size: 14px;
  color: v.$text-muted;
}

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

.item-action {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(74, 125, 224, 0.1);
  font-size: 12px;
  color: #9db8ec;
}
</style>
