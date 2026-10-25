<template>
  <!--
    递归侧边菜单
    - 数据源来自路由 routes（menuRoutes prop），禁止硬编码 menus 数组
    - 有 children → el-sub-menu；叶子 → el-menu-item
    - 过滤：hidden=true 跳过；roles 无权限跳过（连同父分组）
    - 按 meta.sort 升序排序
    - 只处理 layout='default' 的路由，忽略 layout='pda'
  -->
  <template v-for="item in visibleRoutes" :key="resolvePath(item)">
    <!-- 叶子节点：无可见子路由 -->
    <el-menu-item
      v-if="!hasVisibleChildren(item)"
      :index="resolvePath(item)"
      @click="navigate(item)"
    >
      <el-icon v-if="item.meta?.icon">
        <component :is="item.meta.icon" />
      </el-icon>
      <template #title>{{ item.meta?.title }}</template>
    </el-menu-item>

    <!-- 分组节点：有可见子路由 -->
    <el-sub-menu v-else :index="resolvePath(item)">
      <template #title>
        <el-icon v-if="item.meta?.icon">
          <component :is="item.meta.icon" />
        </el-icon>
        <span>{{ item.meta?.title }}</span>
      </template>
      <!-- 递归渲染子菜单 -->
      <SideMenu
        :menu-routes="getVisibleChildren(item)"
        :base-path="resolvePath(item)"
      />
    </el-sub-menu>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { AppRouteRecord } from '@/router/routes'

const props = defineProps<{
  menuRoutes: AppRouteRecord[]
  basePath?: string
}>()

const router = useRouter()
const auth = useAuthStore()

/**
 * 判断某路由是否「可见」
 * 可见 = 非 hidden 且（未声明 roles 或 当前角色有权限）且 非 PDA 布局
 */
function isVisible(route: AppRouteRecord): boolean {
  const meta = route.meta
  if (!meta) return false
  if (meta.hidden) return false
  if (meta.layout === 'pda') return false
  if (meta.roles && meta.roles.length > 0) {
    if (!auth.hasRole(meta.roles)) return false
  }
  return true
}

/** 获取某路由的可见子路由（过滤 + 按 sort 升序） */
function getVisibleChildren(route: AppRouteRecord): AppRouteRecord[] {
  return (route.children ?? [])
    .filter(isVisible)
    .sort((a, b) => (a.meta?.sort ?? 0) - (b.meta?.sort ?? 0))
}

/** 是否有可见子路由（决定渲染 el-sub-menu 还是 el-menu-item） */
function hasVisibleChildren(route: AppRouteRecord): boolean {
  return getVisibleChildren(route).length > 0
}

/** 拼接完整路径 */
function resolvePath(route: AppRouteRecord): string {
  const base = props.basePath ? props.basePath.replace(/\/+$/, '') : ''
  const path = route.path
  if (path.startsWith('/')) return path
  return `${base}/${path}`.replace(/\/+/g, '/')
}

/** 点击叶子节点跳转 */
function navigate(item: AppRouteRecord) {
  const target = resolvePath(item)
  router.push(item.redirect ?? target)
}

// 当前层级的可见菜单（过滤 + 排序）
const visibleRoutes = computed<AppRouteRecord[]>(() =>
  props.menuRoutes.filter(isVisible).sort((a, b) => (a.meta?.sort ?? 0) - (b.meta?.sort ?? 0)),
)
</script>

<style scoped>
/* 递归组件本身不承载视觉，样式由父级 el-menu 控制 */
</style>
