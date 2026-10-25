import type { RouteRecordRaw } from 'vue-router'
import type { AppRouteMeta } from '@/types/models'

// =============================================================================
// 路由树（单一数据源）
// 说明：
//   1. 菜单数据源只能来自本文件的路由 meta，layout 中禁止硬编码 menus 数组。
//   2. 前端权限（roles）仅做「体验拦截」，最终鉴权由后端 A 兜底。
//   3. PDA 作业路由使用独立布局壳（pda），不引入桌面端 Layout。
// =============================================================================

/**
 * 路由 meta 扩展：在 AppRouteMeta 基础上增加「布局壳」标识。
 * layout: 'default'（桌面端布局）/ 'pda'（PDA 独立布局壳）
 */
export interface AppRouteMetaExt extends AppRouteMeta {
  /** 布局壳标识；缺省视为 default */
  layout?: 'default' | 'pda'
}

/** 带扩展 meta 的路由记录类型（保持与 vue-router 兼容） */
export interface AppRouteRecord {
  path: string
  name?: string
  redirect?: string
  component?: RouteRecordRaw['component']
  meta?: AppRouteMetaExt
  children?: AppRouteRecord[]
}

/**
 * 完整路由树
 * 顶层按业务模块分组，group 的 meta 用于侧边菜单分组展示。
 */
export const routes: AppRouteRecord[] = [
  // ========================= 登录页（公开，独立于布局） =========================
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/index.vue'),
    meta: {
      title: '登录',
      public: true,
      hidden: true,
    },
  },

  // ========================= 桌面端布局壳 =========================
  {
    path: '/',
    name: 'root',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      // ---------- 工作台 ----------
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: {
          title: '工作台',
          icon: 'Odometer',
          sort: 1,
          keepAlive: true,
        },
      },

      // ---------- 库存 ----------
      {
        path: 'inventory',
        name: 'inventory',
        component: () => import('@/views/inventory/index.vue'),
        redirect: '/inventory/query',
        meta: { title: '库存', icon: 'Box', sort: 2 },
        children: [
          {
            path: 'query',
            name: 'inventory-query',
            component: () => import('@/views/inventory/query/index.vue'),
            meta: {
              title: '库存查询',
              icon: 'Search',
              sort: 1,
              keepAlive: true,
            },
          },
          {
            path: 'txn',
            name: 'inventory-txn',
            component: () => import('@/views/inventory/txn/index.vue'),
            meta: {
              title: '库存流水',
              icon: 'List',
              sort: 2,
            },
          },
        ],
      },

      // ---------- 入库 ----------
      {
        path: 'inbound',
        name: 'inbound',
        component: () => import('@/views/inbound/index.vue'),
        redirect: '/inbound/order',
        meta: {
          title: '入库',
          icon: 'Download',
          sort: 3,
          roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
        },
        children: [
          {
            path: 'order',
            name: 'inbound-order',
            component: () => import('@/views/inbound/order/index.vue'),
            meta: {
              title: '入库单',
              icon: 'Tickets',
              sort: 1,
              roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
            },
          },
          {
            path: 'putaway',
            name: 'inbound-putaway',
            component: () => import('@/views/inbound/putaway/index.vue'),
            meta: {
              title: '上架作业',
              icon: 'Place',
              sort: 2,
              roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
            },
          },
        ],
      },

      // ---------- 出库 ----------
      {
        path: 'outbound',
        name: 'outbound',
        component: () => import('@/views/outbound/index.vue'),
        redirect: '/outbound/order',
        meta: {
          title: '出库',
          icon: 'Upload',
          sort: 4,
          roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
        },
        children: [
          {
            path: 'order',
            name: 'outbound-order',
            component: () => import('@/views/outbound/order/index.vue'),
            meta: {
              title: '出库单',
              icon: 'Tickets',
              sort: 1,
              roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
            },
          },
          {
            path: 'wave',
            name: 'outbound-wave',
            component: () => import('@/views/outbound/wave/index.vue'),
            meta: {
              title: '波次管理',
              icon: 'Operation',
              sort: 2,
              roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
            },
          },
          {
            path: 'pack',
            name: 'outbound-pack',
            component: () => import('@/views/outbound/pack/index.vue'),
            meta: {
              title: '打包作业',
              icon: 'Box',
              sort: 3,
              roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
            },
          },
        ],
      },

      // ---------- 系统管理 ----------
      {
        path: 'system',
        name: 'system',
        component: () => import('@/views/system/index.vue'),
        redirect: '/system/users',
        meta: {
          title: '系统管理',
          icon: 'Setting',
          sort: 99,
          roles: ['ADMIN'],
        },
        children: [
          {
            path: 'users',
            name: 'system-users',
            component: () => import('@/views/system/users/index.vue'),
            meta: {
              title: '用户角色',
              icon: 'User',
              sort: 1,
              roles: ['ADMIN'],
            },
          },
          {
            path: 'skus',
            name: 'system-skus',
            component: () => import('@/views/system/skus/index.vue'),
            meta: {
              title: '商品主数据',
              icon: 'Goods',
              sort: 2,
              roles: ['ADMIN', 'MANAGER'],
            },
          },
          {
            path: 'locations',
            name: 'system-locations',
            component: () => import('@/views/system/locations/index.vue'),
            meta: {
              title: '库位管理',
              icon: 'Location',
              sort: 3,
              roles: ['ADMIN', 'MANAGER'],
            },
          },
          {
            path: 'audit',
            name: 'system-audit',
            component: () => import('@/views/system/audit/index.vue'),
            meta: {
              title: '审计日志',
              icon: 'Document',
              sort: 4,
              roles: ['ADMIN'],
            },
          },
        ],
      },
    ],
  },

  // ========================= PDA 独立布局壳（不引入桌面端 Layout） =========================
  {
    path: '/pda',
    name: 'pda-root',
    component: () => import('@/layout/pda.vue'),
    redirect: '/pda/scan',
    meta: { layout: 'pda', title: 'PDA 作业', hidden: true },
    children: [
      {
        path: 'scan',
        name: 'pda-scan',
        component: () => import('@/views/pda/scan.vue'),
        meta: {
          title: 'PDA 扫码',
          icon: 'FullScreen',
          layout: 'pda',
          keepAlive: false,
          roles: ['ADMIN', 'MANAGER', 'OPERATOR'],
        },
      },
      {
        // PDA 库存速查（只读）：扫/输 SKU 条码 → 精简列表
        path: 'inventory',
        name: 'pda-inventory',
        component: () => import('@/views/pda/inventory/index.vue'),
        meta: {
          title: '库存速查',
          icon: 'Search',
          layout: 'pda',
          keepAlive: false,
          roles: ['ADMIN', 'MANAGER', 'OPERATOR', 'VIEWER'],
        },
      },
    ],
  },

  // ========================= 403 无权限页（公开，独立于布局） =========================
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/403/index.vue'),
    meta: {
      title: '无权限',
      public: true,
      hidden: true,
    },
  },

  // ========================= 兜底：未匹配路由 =========================
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: '/dashboard',
    meta: { title: '404', hidden: true },
  },
]
