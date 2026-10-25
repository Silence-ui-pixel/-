<template>
  <div class="dashboard">
    <!-- ============ ① 顶部：KPI 统计卡片 ============ -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" class="kpi-card">
        <div class="kpi-icon" :style="{ background: k.bg, color: k.color }">
          <el-icon><component :is="k.icon" /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-label">{{ k.label }}</div>
          <div class="kpi-value">{{ k.value }}</div>
        </div>
      </div>
    </div>

    <!-- ============ ②③ 中部：左步骤条 + 右 AI 助手面板 ============ -->
    <div class="mid-row">
      <!-- 中部左侧：Sprint 进度 -->
      <div class="panel sprint-panel">
        <div class="panel-title">作业 Sprint 进度</div>
        <el-steps direction="vertical" :active="3" finish-status="success" class="sprint-steps">
          <el-step title="现场调研" description="S1-01 ~ S1-04 · 已完成" />
          <el-step title="工程骨架" description="S1-05 / S1-10 · 已完成" />
          <el-step title="契约冻结" description="S1-08 / S1-09 · 进行中" />
          <el-step title="页面开发" description="S1-13 / S1-14 · 待开始" />
        </el-steps>
      </div>

      <!-- 中部右侧：AI 助手面板（只读） -->
      <div class="panel ai-panel">
        <div class="panel-title ai-title">
          <el-icon><MagicStick /></el-icon>
          <span>AI 助手 · 只读提醒</span>
        </div>

        <div class="ai-section">
          <div class="ai-section-head">异常库存提醒</div>
          <div v-for="a in aiAlerts" :key="a.text" class="ai-item">
            <span class="ai-dot" :class="a.level"></span>
            <span class="ai-text">{{ a.text }}</span>
          </div>
        </div>

        <div class="ai-section">
          <div class="ai-section-head">待审批事项</div>
          <div v-for="p in aiApprovals" :key="p.text" class="ai-item">
            <span class="ai-dot ai-dot--pending"></span>
            <span class="ai-text">{{ p.text }}</span>
            <!-- 铁律：只读展示，跳转到对应业务页人工确认，不提供执行按钮 -->
            <el-link type="primary" :underline="false" class="ai-link" @click="goTo(p.route)">
              去处理
            </el-link>
          </div>
        </div>

        <div class="ai-footer">提示：AI 仅提供建议，所有业务修改需跳转业务页人工确认</div>
      </div>
    </div>

    <!-- ============ ④ 底部：近期动态 + 库存预警列表 ============ -->
    <div class="bottom-row">
      <!-- 近期动态 -->
      <div class="panel">
        <div class="panel-title">近期动态</div>
        <el-timeline class="feed">
          <el-timeline-item
            v-for="f in feeds"
            :key="f.text"
            :timestamp="f.time"
            :type="f.type"
          >
            {{ f.text }}
          </el-timeline-item>
        </el-timeline>
      </div>

      <!-- 库存预警列表 -->
      <div class="panel">
        <div class="panel-title">库存预警</div>
        <el-table :data="warnings" size="small" class="warn-table">
          <el-table-column prop="sku" label="商品" />
          <el-table-column prop="loc" label="库位" />
          <el-table-column prop="qty" label="可用量" width="80" align="right" />
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.tag" size="small" effect="dark">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

// ============ ① KPI（Mock 静态数据） ============
const kpis = [
  { label: 'SKU 总数', value: '3', icon: 'Goods', bg: 'rgba(74,125,224,.14)', color: '#6ea0f0' },
  { label: '库位总数', value: '8', icon: 'Location', bg: 'rgba(13,154,168,.14)', color: '#2fc0cf' },
  { label: '库存条目', value: '1', icon: 'Box', bg: 'rgba(109,74,255,.14)', color: '#9d82ff' },
  { label: '待办任务', value: '5', icon: 'Flag', bg: 'rgba(224,138,0,.14)', color: '#f0a83c' },
]

// ============ ③ AI 助手（Mock，只读） ============
const aiAlerts = [
  { text: 'SKU-1003 鲜牛奶 批次 B20261001 剩余效期 12 天', level: 'warn' },
  { text: 'WH01-A-01-01-01 库位 SKU-1001 可用量低于安全库存', level: 'danger' },
]

const aiApprovals = [
  { text: '入库单 IB-20261024-001 待确认收货', route: '/inbound/order' },
  { text: '库存调整申请 ADJ-003 待审批', route: '/inventory/txn' },
]

function goTo(path: string) {
  router.push(path)
}

// ============ ④ 近期动态（Mock） ============
const feeds = [
  { text: '管理员 完成期初库存导入', time: '2026-10-24 20:37', type: 'success' },
  { text: 'AI 助手 生成补货建议（待确认）', time: '2026-10-24 20:40', type: 'primary' },
  { text: '李操作员 提交入库单 IB-20261024-001', time: '2026-10-24 21:02', type: 'warning' },
  { text: '系统 完成库存对账（账实一致）', time: '2026-10-24 22:00', type: 'success' },
]

// ============ ④ 库存预警（Mock） ============
const warnings = [
  { sku: 'SKU-1001 矿泉水', loc: 'WH01-A-01-01-01', qty: 48, status: '低于安全', tag: 'warning' },
  { sku: 'SKU-1003 鲜牛奶', loc: 'WH01-A-00-01-01', qty: 12, status: '临期', tag: 'danger' },
]
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// ============ ① KPI 卡片 ============
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 16px;
  border-radius: 12px;
  background: #161b28;
  border: 1px solid #1f2937;
  transition: border-color 0.25s ease, transform 0.25s ease;
}

.kpi-card:hover {
  border-color: rgba(74, 125, 224, 0.4);
  transform: translateY(-2px);
}

.kpi-icon {
  width: 46px;
  height: 46px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.kpi-info {
  min-width: 0;
}

.kpi-label {
  font-size: 12px;
  color: v.$text-muted;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: v.$text-primary;
  margin-top: 2px;
}

// ============ 中部两栏 ============
.mid-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.panel {
  padding: 16px 18px;
  border-radius: 12px;
  background: #161b28;
  border: 1px solid #1f2937;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;
  margin-bottom: 14px;
}

.sprint-steps {
  :deep(.el-step__title) {
    color: v.$text-primary;
  }
  :deep(.el-step__description) {
    color: v.$text-muted;
  }
}

// AI 面板
.ai-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9d82ff;
}

.ai-section {
  margin-bottom: 14px;
}

.ai-section-head {
  font-size: 12px;
  color: v.$text-muted;
  margin-bottom: 8px;
}

.ai-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  margin-bottom: 6px;
}

.ai-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ai-dot.warn {
  background: #f0a83c;
}

.ai-dot.danger {
  background: #e0607a;
}

.ai-dot--pending {
  background: #6ea0f0;
}

.ai-text {
  flex: 1;
  font-size: 12.5px;
  color: v.$text-secondary;
}

.ai-link {
  flex-shrink: 0;
  font-size: 12px;
}

.ai-footer {
  font-size: 11px;
  color: v.$text-muted;
  padding-top: 8px;
  border-top: 1px solid #1f2937;
}

// ============ 底部两栏 ============
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.feed {
  padding-left: 2px;
  :deep(.el-timeline-item__content) {
    color: v.$text-secondary;
    font-size: 13px;
  }
  :deep(.el-timeline-item__timestamp) {
    color: v.$text-muted;
    font-size: 11px;
  }
}

.warn-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: #1f2937;
  --el-table-header-bg-color: transparent;
  --el-table-text-color: #9aa6bd;
  --el-table-header-text-color: #5f6b82;
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
}

// ============ 响应式 ============
@media (max-width: 992px) {
  .mid-row,
  .bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
