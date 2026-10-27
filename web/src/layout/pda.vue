<script setup lang="ts">
// =============================================================================
// PDA 独立移动端布局壳（H5 手机端外壳）
// - 专供 meta.layout = 'pda' 的路由使用
// - 不复用桌面端侧边栏菜单，仅提供顶部导航栏 + 内容出口
// - 深色低饱和 B 端风格，纯 CSS 动画
// =============================================================================
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

/** 当前页面标题（取自路由 meta.title，缺失时回退默认值） */
const pageTitle = computed(() => (route.meta.title as string) ?? 'PDA 作业')

/** 是否 PDA 首页（首页无返回按钮，它是入口而非子页） */
const isHome = computed(() => route.name === 'pda-home')

/** 返回上一页（无历史记录时回退到工作台） */
function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}
</script>

<template>
  <div class="pda-shell">
    <!-- 顶部导航栏：返回按钮 + 页面标题（首页不显示返回） -->
    <header class="pda-navbar">
      <button v-if="!isHome" class="pda-back" type="button" aria-label="返回" @click="goBack">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden="true">
          <path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <span v-else class="pda-back pda-back--placeholder"></span>
      <span class="pda-title">{{ pageTitle }}</span>
      <!-- 占位，保持标题居中对称 -->
      <span class="pda-back pda-back--placeholder"></span>
    </header>

    <!-- 内容出口 -->
    <main class="pda-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.pda-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh; /* 移动端动态视口高度，避免地址栏遮挡 */
  background: $bg-deep;
  color: $text-primary;
  overflow: hidden;
}

/* ---- 顶部导航栏 ---- */
.pda-navbar {
  position: relative;
  flex: 0 0 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  background: rgba(20, 25, 38, 0.85);
  border-bottom: 1px solid $card-border;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.pda-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  color: $text-secondary;
  border-radius: 10px;
  cursor: pointer;
  transition: color $ease-out 0.25s, background $ease-out 0.25s;
  -webkit-tap-highlight-color: transparent;

  &:hover {
    color: $text-primary;
    background: rgba(255, 255, 255, 0.06);
  }

  &:active {
    background: rgba(255, 255, 255, 0.1);
  }

  /* 右侧占位，保持标题水平居中 */
  &--placeholder {
    visibility: hidden;
  }
}

.pda-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- 内容区 ---- */
.pda-content {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* ---- 系统开启减弱动画时，关闭过渡 ---- */
@media (prefers-reduced-motion: reduce) {
  .pda-back {
    transition: none;
  }
}
</style>
