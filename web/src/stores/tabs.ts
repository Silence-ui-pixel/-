import { defineStore } from 'pinia'
import { ref } from 'vue'

// =============================================================================
// 多标签页（TabsBar）状态管理
// 记录用户打开过的路由标签，支持关闭单个 / 关闭其他 / 关闭全部
// 与 keep-alive 配合：keepAlive 标记的页面组件会被缓存
// =============================================================================

export interface TabItem {
  /** 路由完整路径，作为唯一标识 */
  path: string
  /** 标签标题（来自 route.meta.title） */
  title: string
  /** 路由 name，用于 keep-alive 的 include 匹配 */
  name: string
  /** 是否固定（首页工作台通常不可关闭） */
  affix: boolean
}

export const useTabsStore = defineStore('tabs', () => {
  const tabs = ref<TabItem[]>([])

  /** 新增或激活一个标签（已存在则跳过） */
  function addTab(tab: TabItem) {
    if (!tabs.value.some((t) => t.path === tab.path)) {
      tabs.value.push(tab)
    }
  }

  /** 关闭指定标签（affix 固定标签不可关闭） */
  function closeTab(path: string) {
    const idx = tabs.value.findIndex((t) => t.path === path)
    if (idx === -1) return
    if (tabs.value[idx].affix) return
    tabs.value.splice(idx, 1)
  }

  /** 关闭其他标签（保留当前 + affix 固定标签） */
  function closeOthers(path: string) {
    tabs.value = tabs.value.filter((t) => t.affix || t.path === path)
  }

  /** 关闭全部（保留 affix 固定标签） */
  function closeAll() {
    tabs.value = tabs.value.filter((t) => t.affix)
  }

  /** 清空（登出时调用） */
  function reset() {
    tabs.value = []
  }

  return { tabs, addTab, closeTab, closeOthers, closeAll, reset }
})
