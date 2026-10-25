import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { routes } from './routes'

const router = createRouter({
  history: createWebHistory(),
  // AppRouteRecord 的 meta 是扩展类型（含 layout 字段），结构上兼容 RouteRecordRaw
  routes: routes as RouteRecordRaw[],
})

/**
 * 全局前置守卫
 * 校验顺序：
 *   1. 公开页（public）直接放行；
 *   2. 未登录 → 跳转登录页（携带 redirect 回跳地址）；
 *   3. 已登录访问登录页 → 跳转工作台；
 *   4. 已登录但角色不在路由 meta.roles 内 → 跳转 403。
 *
 * ⚠️ 前端权限仅做「体验拦截」，最终鉴权由后端 A 兜底。
 */
router.beforeEach((to) => {
  const auth = useAuthStore()
  const meta = to.meta as { public?: boolean; roles?: string[] }

  // 1. 公开页直接放行
  if (meta.public === true) {
    // 已登录用户访问登录页，重定向到工作台
    if (auth.isLoggedIn && to.name === 'login') {
      return { name: 'dashboard' }
    }
    return true
  }

  // 2. 未登录 → 登录页
  if (!auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 3. 角色权限校验：路由声明了 roles 且当前角色不在其中 → 403
  if (meta.roles && meta.roles.length > 0) {
    if (!auth.hasRole(meta.roles as Parameters<typeof auth.hasRole>[0])) {
      return { name: 'forbidden' }
    }
  }

  return true
})

export default router
