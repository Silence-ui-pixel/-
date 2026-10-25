<template>
  <!--
    桌面端主布局壳
    结构（自上而下）：
      1. Header 顶栏（56px）：折叠开关 + 面包屑 + 用户下拉
      2. TabsBar 标签页
      3. 左侧 SideMenu 侧边菜单（220px / 折叠 64px）
      4. 主内容区：keep-alive + router-view
    响应式：<768px 侧边栏切换抽屉弹出模式
  -->
  <div class="layout">
    <!-- ============ 侧边栏 ============ -->
    <!-- 桌面：固定侧边栏；移动端：抽屉 -->
    <el-aside
      v-if="!isMobile"
      :width="collapsed ? '64px' : '220px'"
      class="sidebar"
    >
      <div class="logo" @click="router.push('/dashboard')">
        <div class="logo-mark">W</div>
        <span v-show="!collapsed" class="logo-text">智慧仓管</span>
      </div>
      <el-scrollbar class="sidebar-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          :collapse-transition="false"
          router
          class="menu"
        >
          <SideMenu :menu-routes="menuRoutes" base-path="/" />
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <!-- 移动端抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      v-if="isMobile"
      direction="ltr"
      :size="220"
      :with-header="false"
      class="mobile-drawer"
    >
      <div class="logo" @click="router.push('/dashboard')">
        <div class="logo-mark">W</div>
        <span class="logo-text">智慧仓管</span>
      </div>
      <el-menu :default-active="activeMenu" router class="menu">
        <SideMenu :menu-routes="menuRoutes" base-path="/" />
      </el-menu>
    </el-drawer>

    <!-- ============ 右侧主体 ============ -->
    <div class="main-wrap">
      <!-- Header 顶栏 -->
      <header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="toggleSidebar">
            <component :is="collapseIcon" />
          </el-icon>
          <!-- 面包屑 -->
          <el-breadcrumb class="breadcrumb" separator="/">
            <el-breadcrumb-item v-for="(item, i) in breadcrumbs" :key="item.path">
              <span :class="{ 'crumb-current': i === breadcrumbs.length - 1 }">
                {{ item.title }}
              </span>
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-tag size="small" type="info" effect="plain">P0 · 骨架阶段</el-tag>
          <el-dropdown @command="onCommand">
            <span class="user-chip">
              <el-icon><User /></el-icon>
              {{ auth.user?.displayName || '未登录' }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  角色：{{ auth.user?.role || '-' }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- TabsBar 标签页 -->
      <TabsBar />

      <!-- 主内容区 -->
      <main class="content">
        <router-view v-slot="{ Component, route: r }">
          <keep-alive :include="cachedViews">
            <component :is="Component" :key="r.path" />
          </keep-alive>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useTabsStore } from '@/stores/tabs'
import { routes, type AppRouteRecord } from '@/router/routes'
import SideMenu from './components/SideMenu.vue'
import TabsBar from './components/TabsBar.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tabsStore = useTabsStore()

const collapsed = ref(false)
const isMobile = ref(false)
const drawerVisible = ref(false)

// ============ 菜单数据源（来自路由 meta，禁止硬编码） ============
// 取桌面布局壳（/ 根路由）的 children 作为一级菜单
const menuRoutes = computed<AppRouteRecord[]>(() => {
  const root = routes.find((r) => r.path === '/')
  return root?.children ?? []
})

const activeMenu = computed(() => route.path)
const collapseIcon = computed(() => (isMobile.value ? 'Expand' : collapsed.value ? 'Expand' : 'Fold'))

// ============ 面包屑（根据 route.matched 自动生成） ============
const breadcrumbs = computed(() => {
  return route.matched
    .filter((r) => r.meta?.title)
    .map((r) => ({
      path: r.path,
      title: r.meta.title as string,
    }))
})

// ============ keep-alive 缓存名单（来自 meta.keepAlive） ============
const cachedViews = computed(() => {
  const names: string[] = []
  const collect = (list: AppRouteRecord[]) => {
    for (const r of list) {
      if (r.meta?.keepAlive && r.name) names.push(r.name as string)
      if (r.children) collect(r.children)
    }
  }
  collect(routes)
  return names
})

// ============ 响应式：检测屏幕宽度 ============
function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) drawerVisible.value = false
}

function toggleSidebar() {
  if (isMobile.value) {
    drawerVisible.value = !drawerVisible.value
  } else {
    collapsed.value = !collapsed.value
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

// ============ 记录标签页 ============
watch(
  () => route.fullPath,
  () => {
    if (route.meta?.title && route.name) {
      tabsStore.addTab({
        path: route.path,
        title: route.meta.title as string,
        name: route.name as string,
        affix: route.path === '/dashboard',
      })
    }
  },
  { immediate: true },
)

// ============ 用户下拉 ============
function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    tabsStore.reset()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.layout {
  display: flex;
  height: 100vh;
  background: v.$bg-deep;
  overflow: hidden;
}

// ============ 侧边栏 ============
.sidebar {
  display: flex;
  flex-direction: column;
  background: #141926;
  border-right: 1px solid #1f2937;
  transition: width 0.2s ease;
  overflow: hidden;
  flex-shrink: 0;
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  cursor: pointer;
  color: #fff;
  flex-shrink: 0;
}

.logo-mark {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: v.$brand;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
}

.sidebar-scroll {
  flex: 1;
}

.menu {
  border-right: none;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #9aa6bd;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-active-color: #fff;
  --el-menu-item-height: 46px;
  --el-menu-sub-item-height: 42px;
}

.menu :deep(.el-menu-item.is-active),
.menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  background: rgba(74, 125, 224, 0.18);
  color: #fff;
}

.menu :deep(.el-menu-item),
.menu :deep(.el-sub-menu__title) {
  color: #9aa6bd;
}

.menu :deep(.el-menu-item:hover),
.menu :deep(.el-sub-menu__title:hover) {
  color: #e8ecf4;
}

// ============ 主体 ============
.main-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

// ============ 顶栏 ============
.header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #141926;
  border-bottom: 1px solid #1f2937;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.collapse-btn {
  font-size: 18px;
  cursor: pointer;
  color: #9aa6bd;
  transition: color 0.2s ease;
}

.collapse-btn:hover {
  color: #e8ecf4;
}

.breadcrumb {
  font-size: 13px;
}

.breadcrumb :deep(.el-breadcrumb__inner) {
  color: #5f6b82;
  font-weight: 400;
}

.breadcrumb :deep(.crumb-current) {
  color: #e8ecf4;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #e8ecf4;
  cursor: pointer;
  outline: none;
}

// ============ 内容区 ============
.content {
  flex: 1;
  padding: 16px;
  overflow: auto;
  background: v.$bg-deep;
}

// ============ 移动端抽屉 ============
:deep(.mobile-drawer) {
  .el-drawer__body {
    padding: 0;
    background: #141926;
  }
}

// ============ 响应式 ============
@media (max-width: 768px) {
  .header {
    padding: 0 12px;
  }
  .content {
    padding: 12px;
  }
}
</style>
