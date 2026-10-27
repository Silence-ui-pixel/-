<template>
  <div class="board" v-loading="loading">
    <!-- ============ ① KPI ============ -->
    <section class="kpi-row">
      <div v-for="k in kpis" :key="k.label" class="kpi-card" :class="k.tone && `tone-${k.tone}`">
        <div class="kpi-head">
          <span class="kpi-label">{{ k.label }}</span>
          <el-icon v-if="k.icon" class="kpi-icon"><component :is="k.icon" /></el-icon>
        </div>
        <div class="kpi-value">
          {{ k.value }}<span v-if="k.unit" class="kpi-unit">{{ k.unit }}</span>
        </div>
        <div class="kpi-sub">{{ k.sub }}</div>
      </div>
    </section>

    <!-- ============ ② 库存健康度 ============ -->
    <section class="row-2">
      <!-- 效期分层 -->
      <div class="panel">
        <div class="panel-title">
          <span>效期健康度</span>
          <span class="panel-hint">按可用量分层 · 共 {{ totals.dims }} 个库存维度</span>
        </div>

        <div class="shelf">
          <div v-for="b in expiryBuckets" :key="b.key" class="shelf-row">
            <span class="shelf-name">{{ b.label }}</span>
            <div class="shelf-track">
              <div class="shelf-bar" :class="`bar-${b.tone}`" :style="{ width: pct(b.qty) }"></div>
            </div>
            <span class="shelf-qty">{{ b.qty }}</span>
            <span class="shelf-dims">{{ b.dims }} 维</span>
          </div>
        </div>

        <!-- 主数据重复提示 -->
        <div v-if="dupGroups.length" class="warn-strip">
          <el-icon><WarningFilled /></el-icon>
          <span>
            主数据疑似重复 {{ dupGroups.length }} 组：{{ dupGroups.map((g) => g.codes.join(' / ')).join('；') }}
          </span>
        </div>
      </div>

      <!-- ABC 结构 -->
      <div class="panel">
        <div class="panel-title">
          <span>ABC 结构</span>
          <span class="panel-hint">按可用量占全仓比重</span>
        </div>

        <div class="shelf">
          <div v-for="a in abcBuckets" :key="a.key" class="shelf-row">
            <span class="shelf-name">{{ a.label }}</span>
            <div class="shelf-track">
              <div class="shelf-bar" :class="`bar-abc-${a.key.toLowerCase()}`" :style="{ width: pct(a.qty) }"></div>
            </div>
            <span class="shelf-qty">{{ a.qty }}</span>
            <span class="shelf-dims">{{ a.share }}%</span>
          </div>
        </div>

        <div class="mini-stats">
          <div class="mini">
            <span class="mini-num">{{ totals.onHand }}</span>
            <span class="mini-label">现有合计</span>
          </div>
          <div class="mini">
            <span class="mini-num">{{ totals.allocated }}</span>
            <span class="mini-label">已分配</span>
          </div>
          <div class="mini">
            <span class="mini-num accent">{{ totals.available }}</span>
            <span class="mini-label">可用合计</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ ③ 补货预警 + 过期明细 ============ -->
    <section class="row-2">
      <!-- 补货预警 -->
      <div class="panel">
        <div class="panel-title">
          <span>补货预警</span>
          <span class="panel-hint">口径：可用 &lt; 安全库存</span>
        </div>
        <el-table :data="replenishRows" size="small" class="data-table" empty-text="全部商品库存充足">
          <el-table-column prop="sku_code" label="SKU" width="135">
            <template #default="{ row }">
              <span class="mono">{{ row.sku_code }}</span>
              <el-tag v-if="dupCodes.has(row.sku_code)" size="small" type="warning" class="dup-tag">重码</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="110" show-overflow-tooltip />
          <el-table-column label="可用 / 安全" width="115" align="right">
            <template #default="{ row }">
              <span class="qty-avail">{{ row.available }}</span>
              <span class="qty-sep">/</span>
              <span class="qty-safe">{{ row.safety }}</span>
            </template>
          </el-table-column>
          <el-table-column label="缺口" width="80" align="right">
            <template #default="{ row }">
              <span class="gap">-{{ row.gap }}</span>
            </template>
          </el-table-column>
          <el-table-column label="ABC" width="62" align="center">
            <template #default="{ row }">
              <el-tag :type="abcTag(row.abc)" size="small">{{ row.abc || '—' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 过期明细 -->
      <div class="panel">
        <div class="panel-title">
          <span>已过期批次</span>
          <span class="panel-hint">按逾期天数排序 · 共 {{ expiredRows.length }} 批 / {{ totals.expiredQty }} 件</span>
        </div>
        <el-table :data="expiredRows" size="small" class="data-table" empty-text="没有过期批次">
          <el-table-column prop="sku_code" label="SKU" width="105">
            <template #default="{ row }">
              <span class="mono">{{ row.sku_code }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="location_code" label="库位" width="82">
            <template #default="{ row }">
              <span class="mono">{{ row.location_code }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="batch_no" label="批次" width="112">
            <template #default="{ row }">
              <span class="mono">{{ row.batch_no || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="效期" width="100">
            <template #default="{ row }">{{ row.expiry_date }}</template>
          </el-table-column>
          <el-table-column label="逾期" width="82" align="right">
            <template #default="{ row }">
              <span class="overdue">{{ row.overdue }} 天</span>
            </template>
          </el-table-column>
          <el-table-column label="可用" width="70" align="right">
            <template #default="{ row }">{{ row.available }}</template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <!-- ============ ④ 近期作业流水 ============ -->
    <section class="panel">
      <div class="panel-title">
        <span>近期作业流水</span>
        <span class="panel-hint">只追加账本 · 最近 {{ recentTxns.length }} 条</span>
      </div>
      <el-table :data="recentTxns" size="small" class="data-table" empty-text="暂无流水">
        <el-table-column label="时间" width="150">
          <template #default="{ row }">
            <span class="time-text">{{ fmtTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="txnTag(row.txn_type)" size="small" effect="plain">
              {{ TXN_TEXT[row.txn_type as string] ?? row.txn_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sku_code" label="SKU" width="105">
          <template #default="{ row }">
            <span class="mono">{{ row.sku_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="location_code" label="库位" width="82">
          <template #default="{ row }">
            <span class="mono">{{ row.location_code }}</span>
          </template>
        </el-table-column>
        <el-table-column label="现有量变动" width="105" align="right">
          <template #default="{ row }">
            <span :class="deltaClass(row.on_hand_delta)">{{ fmtDelta(row.on_hand_delta) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分配量变动" width="105" align="right">
          <template #default="{ row }">
            <span :class="deltaClass(row.allocated_delta)">{{ fmtDelta(row.allocated_delta) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="变动后现存量" width="115" align="right">
          <template #default="{ row }">{{ row.after_on_hand }}</template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="82" align="center" />
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 库存健康 + 作业看板（报表看板）
// - 数据源：GET /inventory、/skus、/stock-txn、/inbound-orders、/outbound-orders、/inventory/recon
// - 全部前端聚合：数据量小（14 个库存维度），无需后端加聚合接口（B 不改后端）
// - 口径：可用 = 现有 − 已分配（生成列只读，前端不自行计算库存）
// - 效期哨兵 9999-12-30 表示不管理效期，不计入过期/临期
// - 补货按「可用 < 安全库存」；现场数据 reorder_point < safety_stock 疑为录入颠倒，故不用补货点
// =============================================================================
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { client, ApiError } from '@/api/client'
import type { components } from '@/api/schema'

type InventoryItem = components['schemas']['InventoryItem']
type Sku = components['schemas']['Sku']
type StockTxnItem = components['schemas']['StockTxnItem']
type InboundOrder = components['schemas']['InboundOrder']
type OutboundOrder = components['schemas']['OutboundOrder']
type ReconItem = components['schemas']['ReconItem']

const loading = ref(false)
const inventory = ref<InventoryItem[]>([])
const skus = ref<Sku[]>([])
const txns = ref<StockTxnItem[]>([])
const inbound = ref<InboundOrder[]>([])
const outbound = ref<OutboundOrder[]>([])
const recon = ref<ReconItem[] | null>(null)

const TXN_TEXT: Record<string, string> = {
  RECEIPT: '收货',
  PUTAWAY: '上架',
  PICK: '拣货',
  SHIP: '发运',
  ADJUST: '调整',
  TRANSFER_IN: '移入',
  TRANSFER_OUT: '移出',
  COUNT_ADJUST: '盘点调整',
  ALLOCATE: '分配',
  DEALLOCATE: '解分配',
}

const SENTINEL = '9999-12-30'

/** 今天 00:00（本地） */
function todayStart(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

function daysBetween(from: string, to: Date): number {
  const a = new Date(from + 'T00:00:00')
  return Math.round((to.getTime() - a.getTime()) / 86400000)
}

/* ---------- 汇总 ---------- */
const totals = computed(() => {
  let onHand = 0
  let allocated = 0
  let available = 0
  let expiredQty = 0
  for (const r of inventory.value) {
    onHand += Number(r.qty_on_hand ?? 0)
    allocated += Number(r.qty_allocated ?? 0)
    available += Number(r.qty_available ?? 0)
  }
  for (const r of expiredRows.value) expiredQty += r.available
  return { onHand, allocated, available, expiredQty, dims: inventory.value.length }
})

/* ---------- 效期分层 ---------- */
const expiryBuckets = computed(() => {
  const today = todayStart()
  const buckets = {
    expired: { key: 'expired', label: '已过期', tone: 'danger', qty: 0, dims: 0 },
    d30: { key: 'd30', label: '30 天内到期', tone: 'warn', qty: 0, dims: 0 },
    d90: { key: 'd90', label: '90 天内到期', tone: 'attention', qty: 0, dims: 0 },
    normal: { key: 'normal', label: '正常', tone: 'ok', qty: 0, dims: 0 },
    none: { key: 'none', label: '不管理效期', tone: 'muted', qty: 0, dims: 0 },
  }
  for (const r of inventory.value) {
    const qty = Number(r.qty_available ?? 0)
    const exp = r.expiry_date ?? SENTINEL
    if (!exp || exp.startsWith('9999')) {
      buckets.none.qty += qty
      buckets.none.dims += 1
      continue
    }
    const days = daysBetween(exp, today)
    if (days < 0) {
      buckets.expired.qty += qty
      buckets.expired.dims += 1
    } else if (days <= 30) {
      buckets.d30.qty += qty
      buckets.d30.dims += 1
    } else if (days <= 90) {
      buckets.d90.qty += qty
      buckets.d90.dims += 1
    } else {
      buckets.normal.qty += qty
      buckets.normal.dims += 1
    }
  }
  return Object.values(buckets)
})

function pct(qty: number): string {
  const max = Math.max(...expiryBuckets.value.map((b) => b.qty), 1)
  return `${Math.max((qty / max) * 100, qty > 0 ? 2 : 0)}%`
}

/* ---------- ABC 结构 ---------- */
const abcBuckets = computed(() => {
  const map: Record<string, number> = { A: 0, B: 0, C: 0, '—': 0 }
  const bySku = new Map<string, string>()
  for (const s of skus.value) bySku.set(s.sku_code ?? '', s.abc_class ?? '—')
  for (const r of inventory.value) {
    const abc = bySku.get(r.sku_code ?? '') || '—'
    map[abc] = (map[abc] ?? 0) + Number(r.qty_available ?? 0)
  }
  const total = Object.values(map).reduce((a, b) => a + b, 0) || 1
  return (['A', 'B', 'C'] as const).map((k) => ({
    key: k,
    label: `${k} 类`,
    qty: map[k] ?? 0,
    share: Math.round(((map[k] ?? 0) / total) * 100),
  }))
})

/* ---------- 主数据重复（同名不同编码） ---------- */
const dupGroups = computed(() => {
  const byName = new Map<string, Set<string>>()
  for (const s of skus.value) {
    const name = (s.name ?? '').replace(/\s+/g, '')
    if (!name) continue
    if (!byName.has(name)) byName.set(name, new Set())
    byName.get(name)!.add(s.sku_code ?? '')
  }
  const groups: Array<{ name: string; codes: string[] }> = []
  for (const [name, codes] of byName) {
    if (codes.size > 1) groups.push({ name, codes: [...codes] })
  }
  // 抽纸/纸巾、鲜牛奶/牛奶 这类名称不完全相同但同商品的，用关键词粗略兜底
  const nearDup: Array<[string, string]> = [
    ['抽纸', '纸巾'],
    ['鲜牛奶', '牛奶'],
  ]
  for (const [a, b] of nearDup) {
    const ca = skus.value.filter((s) => s.name?.includes(a)).map((s) => s.sku_code ?? '')
    const cb = skus.value.filter((s) => s.name?.includes(b) && !s.name?.includes(a)).map((s) => s.sku_code ?? '')
    if (ca.length && cb.length) groups.push({ name: `${a}/${b}`, codes: [...ca, ...cb] })
  }
  return groups
})

/* ---------- 补货预警 ---------- */
/** 重码 SKU 集合（补货预警里标注，提示该需求可能是主数据重复造成的） */
const dupCodes = computed(() => {
  const set = new Set<string>()
  for (const g of dupGroups.value) for (const c of g.codes) if (c) set.add(c)
  return set
})

const replenishRows = computed(() => {
  const availBySku = new Map<string, number>()
  for (const r of inventory.value) {
    const k = r.sku_code ?? ''
    availBySku.set(k, (availBySku.get(k) ?? 0) + Number(r.qty_available ?? 0))
  }
  const rows: Array<{
    sku_code: string
    name: string
    available: number
    safety: number
    gap: number
    abc: string
  }> = []
  for (const s of skus.value) {
    const safety = Number(s.safety_stock ?? 0)
    if (!safety) continue
    const available = availBySku.get(s.sku_code ?? '') ?? 0
    if (available < safety) {
      rows.push({
        sku_code: s.sku_code ?? '',
        name: s.name ?? '',
        available,
        safety,
        gap: safety - available,
        abc: s.abc_class ?? '',
      })
    }
  }
  return rows.sort((a, b) => b.gap - a.gap)
})

/* ---------- 过期批次 ---------- */
const expiredRows = computed(() => {
  const today = todayStart()
  const rows: Array<{
    sku_code: string
    location_code: string
    batch_no: string
    expiry_date: string
    overdue: number
    available: number
  }> = []
  for (const r of inventory.value) {
    const exp = r.expiry_date ?? ''
    if (!exp || exp.startsWith('9999')) continue
    const days = daysBetween(exp, today)
    if (days >= 0) continue
    rows.push({
      sku_code: r.sku_code ?? '',
      location_code: r.location_code ?? '',
      batch_no: r.batch_no ?? '',
      expiry_date: exp,
      overdue: Math.abs(days),
      available: Number(r.qty_available ?? 0),
    })
  }
  return rows.sort((a, b) => b.overdue - a.overdue)
})

/* ---------- 待处理单据 ---------- */
const pending = computed(() => {
  const waitReceive = inbound.value.filter((o) =>
    ['DRAFT', 'ARRIVED', 'RECEIVING'].includes(o.status ?? ''),
  ).length
  const waitPutaway = inbound.value.filter((o) => o.status === 'RECEIVED').length
  const waitPick = outbound.value.filter((o) => o.status === 'ALLOCATED').length
  const waitShip = outbound.value.filter((o) => o.status === 'PICKED').length
  return { waitReceive, waitPutaway, waitPick, waitShip, total: waitReceive + waitPutaway + waitPick + waitShip }
})

/* ---------- 近期流水 ---------- */
const recentTxns = computed(() => txns.value.slice(0, 10))

/* ---------- KPI ---------- */
const kpis = computed(() => {
  const reconOk = recon.value?.filter((r) => r.recon_status === 'OK').length ?? 0
  const reconTotal = recon.value?.length ?? 0
  return [
    {
      label: '可用库存',
      value: totals.value.available,
      unit: ' 件',
      sub: `现有 ${totals.value.onHand} · 已分配 ${totals.value.allocated}`,
      icon: 'Box',
    },
    {
      label: '已过期批次',
      value: expiredRows.value.length,
      unit: ' 批',
      sub: `可用量 ${totals.value.expiredQty} 件待处理`,
      tone: expiredRows.value.length ? 'danger' : undefined,
      icon: 'WarningFilled',
    },
    {
      label: '90 天内到期',
      value: (expiryBuckets.value[1]?.dims ?? 0) + (expiryBuckets.value[2]?.dims ?? 0),
      unit: ' 批',
      sub: `可用量 ${(expiryBuckets.value[1]?.qty ?? 0) + (expiryBuckets.value[2]?.qty ?? 0)} 件`,
      tone: 'warn',
      icon: 'Clock',
    },
    {
      label: '低于安全库存',
      value: replenishRows.value.length,
      unit: ' 个 SKU',
      sub: replenishRows.value.length ? `最大缺口 ${replenishRows.value[0]?.gap ?? 0} 件` : '全部充足',
      tone: replenishRows.value.length ? 'warn' : 'ok',
      icon: 'TrendCharts',
    },
    {
      label: '待处理单据',
      value: pending.value.total,
      unit: ' 张',
      sub: `待收货 ${pending.value.waitReceive} · 待上架 ${pending.value.waitPutaway} · 待拣 ${pending.value.waitPick} · 待发 ${pending.value.waitShip}`,
      icon: 'Tickets',
    },
    {
      label: '账实一致',
      value: reconTotal ? `${reconOk}/${reconTotal}` : '—',
      unit: '',
      sub: reconTotal ? (reconOk === reconTotal ? '全部一致' : `${reconTotal - reconOk} 条异常`) : '需主管权限',
      tone: reconTotal && reconOk !== reconTotal ? 'danger' : 'ok',
      icon: 'CircleCheck',
    },
  ]
})

/* ---------- 工具 ---------- */
function abcTag(abc: string): 'danger' | 'warning' | 'info' {
  if (abc === 'A') return 'danger'
  if (abc === 'B') return 'warning'
  return 'info'
}

function txnTag(t: unknown): 'success' | 'warning' | 'info' | 'danger' | 'primary' {
  const map: Record<string, 'success' | 'warning' | 'info' | 'danger' | 'primary'> = {
    RECEIPT: 'success',
    PUTAWAY: 'primary',
    PICK: 'warning',
    SHIP: 'danger',
    ALLOCATE: 'info',
    DEALLOCATE: 'info',
  }
  return map[t as string] ?? 'info'
}

function fmtDelta(v: unknown): string {
  const n = Number(v ?? 0)
  if (!n) return '0'
  return n > 0 ? `+${n}` : `${n}`
}

function deltaClass(v: unknown): string {
  const n = Number(v ?? 0)
  if (n > 0) return 'delta-up'
  if (n < 0) return 'delta-down'
  return 'delta-zero'
}

function fmtTime(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/* ---------- 加载 ---------- */
async function loadAll() {
  loading.value = true
  try {
    const [inv, sku, txn, inb, outb] = await Promise.all([
      client.GET('/inventory', { params: { query: { page: 1, page_size: 100 } } }),
      client.GET('/skus', { params: { query: { page: 1, page_size: 100 } } }),
      client.GET('/stock-txn', { params: { query: { page: 1, page_size: 100 } } }),
      client.GET('/inbound-orders', { params: { query: { page: 1, page_size: 100 } } }),
      client.GET('/outbound-orders', { params: { query: { page: 1, page_size: 100 } } }),
    ])
    inventory.value = inv.data?.items ?? []
    skus.value = sku.data?.items ?? []
    txns.value = txn.data?.items ?? []
    inbound.value = inb.data?.items ?? []
    outbound.value = outb.data?.items ?? []
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载看板数据失败')
  } finally {
    loading.value = false
  }

  // 对账需 MANAGER/ADMIN，无权限时静默跳过（不阻塞看板）
  try {
    const { data } = await client.GET('/inventory/recon')
    recon.value = data?.items ?? []
  } catch {
    recon.value = null
  }
}

onMounted(loadAll)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.board {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------- KPI ---------- */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}

.kpi-card {
  padding: 14px 15px 13px;
  border-radius: 12px;
  background: rgba(24, 29, 42, 0.72);
  border: 1px solid v.$card-border;
  transition: border-color 0.2s, transform 0.2s;

  &:hover {
    transform: translateY(-2px);
    border-color: rgba(74, 125, 224, 0.38);
  }

  &.tone-danger {
    border-color: rgba(224, 108, 108, 0.42);
    background: rgba(224, 108, 108, 0.07);
  }

  &.tone-warn {
    border-color: rgba(240, 167, 90, 0.34);
  }

  &.tone-ok {
    border-color: rgba(111, 211, 155, 0.28);
  }
}

.kpi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-label {
  font-size: 12px;
  color: v.$text-muted;
}

.kpi-icon {
  font-size: 14px;
  color: v.$text-muted;
  opacity: 0.7;
}

.kpi-value {
  margin-top: 6px;
  font-size: 25px;
  font-weight: 700;
  line-height: 1.1;
  color: v.$text-primary;
}

.tone-danger .kpi-value {
  color: #e06c6c;
}

.kpi-unit {
  font-size: 12px;
  font-weight: 400;
  color: v.$text-muted;
  margin-left: 3px;
}

.kpi-sub {
  margin-top: 5px;
  font-size: 11px;
  line-height: 1.45;
  color: v.$text-muted;
}

/* ---------- 面板 ---------- */
.row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.panel {
  background: rgba(24, 29, 42, 0.72);
  border: 1px solid v.$card-border;
  border-radius: 12px;
  padding: 16px 18px;
}

.panel-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;
}

.panel-hint {
  font-size: 11.5px;
  font-weight: 400;
  color: v.$text-muted;
}

/* ---------- 条形图（纯 CSS，无图表库依赖） ---------- */
.shelf {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.shelf-row {
  display: grid;
  grid-template-columns: 90px 1fr 58px 52px;
  align-items: center;
  gap: 10px;
}

.shelf-name {
  font-size: 12px;
  color: v.$text-secondary;
  white-space: nowrap;
}

.shelf-track {
  height: 9px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.shelf-bar {
  height: 100%;
  border-radius: 5px;
  transition: width 0.4s ease;
}

.bar-danger {
  background: linear-gradient(90deg, #e0607a, #e06c6c);
}

.bar-warn {
  background: linear-gradient(90deg, #f0a75a, #e08a00);
}

.bar-attention {
  background: linear-gradient(90deg, #f0d05a, #e0b800);
}

.bar-ok {
  background: linear-gradient(90deg, #6fd39b, #38a877);
}

.bar-muted {
  background: rgba(138, 148, 168, 0.5);
}

.bar-abc-a {
  background: linear-gradient(90deg, #6ea0f0, #4a7de0);
}

.bar-abc-b {
  background: linear-gradient(90deg, #2fc0cf, #0d9aa8);
}

.bar-abc-c {
  background: rgba(138, 148, 168, 0.6);
}

.shelf-qty {
  font-size: 12.5px;
  font-weight: 600;
  color: v.$text-primary;
  text-align: right;
}

.shelf-dims {
  font-size: 11px;
  color: v.$text-muted;
  text-align: right;
}

/* ---------- 主数据重复提示 ---------- */
.warn-strip {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 14px;
  padding: 9px 11px;
  border-radius: 8px;
  background: rgba(240, 167, 90, 0.1);
  border: 1px solid rgba(240, 167, 90, 0.26);
  font-size: 11.5px;
  line-height: 1.55;
  color: #f0c48a;
}

/* ---------- 迷你统计 ---------- */
.mini-stats {
  display: flex;
  gap: 26px;
  margin-top: 16px;
  padding-top: 13px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.mini {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mini-num {
  font-size: 18px;
  font-weight: 700;
  color: v.$text-primary;

  &.accent {
    color: #6fd39b;
  }
}

.mini-label {
  font-size: 11px;
  color: v.$text-muted;
}

/* ---------- 表格 ---------- */
.data-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: rgba(255, 255, 255, 0.06);
  --el-table-header-bg-color: transparent;
  --el-table-text-color: #9aa6bd;
  --el-table-header-text-color: #5f6b82;
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
}

.mono {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  color: v.$text-primary;
}

.qty-avail {
  color: #f0a75a;
  font-weight: 600;
}

.qty-sep {
  margin: 0 4px;
  color: v.$text-muted;
}

.qty-safe {
  color: v.$text-muted;
}

.gap {
  color: #e06c6c;
  font-weight: 600;
}

.dup-tag {
  margin-left: 5px;
  transform: scale(0.85);
  transform-origin: left center;
}

.overdue {
  color: #e06c6c;
  font-weight: 600;
  font-size: 12px;
}

.time-text {
  font-size: 11.5px;
  color: v.$text-muted;
}

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

/* ---------- 响应式 ---------- */
@media (max-width: 1400px) {
  .kpi-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .row-2 {
    grid-template-columns: 1fr;
  }
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
