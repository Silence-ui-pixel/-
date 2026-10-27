<template>
  <div class="pda-home">
    <!-- ========== 问候区 ========== -->
    <section class="greeting">
      <div class="hello">{{ greeting }}，{{ displayName }}</div>
      <div class="sub">
        <span class="role-badge">{{ roleText }}</span>
        <span class="date">{{ today }}</span>
      </div>
    </section>

    <!-- ========== 功能卡 ========== -->
    <section class="card-grid">
      <button
        v-for="card in cards"
        :key="card.name"
        type="button"
        class="feature-card"
        @click="router.push(card.path)"
      >
        <span class="card-icon">
          <el-icon><component :is="card.icon" /></el-icon>
        </span>
        <span class="card-title">{{ card.title }}</span>
        <span class="card-desc">{{ card.desc }}</span>
      </button>
    </section>

    <!-- ========== 底部提示 ========== -->
    <div class="footer-tip">演示环境 · 数据来自本地后端</div>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// PDA 首页（作业入口）
// - 解决「PDA 各页面之间没有导航入口、只能手输 URL」的可用性缺口
// - 按当前登录角色过滤功能卡（VIEWER 只能看库存速查）
// - 纯 UI，不请求业务接口；用户信息取自 auth store（登录时已拉取）
// =============================================================================
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/types/models'

const router = useRouter()
const auth = useAuthStore()

const ROLE_TEXT: Record<UserRole, string> = {
  ADMIN: '系统管理员',
  MANAGER: '仓管主管',
  OPERATOR: '操作员',
  VIEWER: '只读访客',
}

const displayName = computed(() => auth.user?.displayName ?? '未登录')
const roleText = computed(() => (auth.role ? ROLE_TEXT[auth.role] : '—'))

/** 按时段问候 */
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const today = computed(() => {
  const d = new Date()
  return `${d.getMonth() + 1}月${d.getDate()}日 周${'日一二三四五六'[d.getDay()]}`
})

interface FeatureCard {
  name: string
  title: string
  desc: string
  icon: string
  path: string
  roles: UserRole[]
}

const ALL_CARDS: FeatureCard[] = [
  {
    name: 'inventory',
    title: '库存速查',
    desc: '扫码查可用库存',
    icon: 'Search',
    path: '/pda/inventory',
    roles: ['ADMIN', 'MANAGER', 'OPERATOR', 'VIEWER'],
  },
  {
    name: 'inbound',
    title: '入库作业',
    desc: '收货 · 上架',
    icon: 'Download',
    path: '/pda/inbound',
    roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
  },
  {
    name: 'outbound',
    title: '出库作业',
    desc: '拣货 · 发运',
    icon: 'Upload',
    path: '/pda/outbound',
    roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
  },
  {
    name: 'scan',
    title: '扫码识别',
    desc: '扫条码看明细',
    icon: 'FullScreen',
    path: '/pda/scan',
    roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
  },
]

const cards = computed(() => ALL_CARDS.filter((c) => auth.hasRole(c.roles)))
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.pda-home {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  padding: 18px 16px 24px;
  box-sizing: border-box;
}

/* ---------- 问候区 ---------- */
.greeting {
  margin-bottom: 22px;
}

.hello {
  font-size: 22px;
  font-weight: 700;
  color: v.$text-primary;
  letter-spacing: 0.5px;
}

.sub {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.role-badge {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(74, 125, 224, 0.16);
  border: 1px solid rgba(74, 125, 224, 0.35);
  color: #9db8ec;
  font-size: 12px;
  font-weight: 600;
}

.date {
  font-size: 12px;
  color: v.$text-muted;
}

/* ---------- 功能卡 ---------- */
.card-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  flex: 1;
  align-content: start;
}

.feature-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 18px 16px;
  min-height: 120px;
  border-radius: 16px;
  border: 1px solid v.$card-border;
  background: rgba(24, 29, 42, 0.82);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.2s ease, background 0.2s ease;
  -webkit-tap-highlight-color: transparent;

  &:active {
    transform: scale(0.97);
    background: rgba(74, 125, 224, 0.14);
    border-color: rgba(74, 125, 224, 0.45);
  }
}

.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(74, 125, 224, 0.14);
  color: #7fa6ec;
  font-size: 22px;
  margin-bottom: 4px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: v.$text-primary;
}

.card-desc {
  font-size: 12px;
  color: v.$text-muted;
}

/* ---------- 底部提示 ---------- */
.footer-tip {
  margin-top: 24px;
  text-align: center;
  font-size: 11px;
  color: v.$text-muted;
  opacity: 0.7;
}

/* ---------- 减弱动画 ---------- */
@media (prefers-reduced-motion: reduce) {
  .feature-card {
    transition: none;
  }
}
</style>
