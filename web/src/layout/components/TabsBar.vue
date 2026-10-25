<template>
  <!--
    多标签页栏
    - 记录已打开的路由标签
    - 支持关闭单个 / 关闭其他 / 关闭全部
    - 与 keep-alive 配合缓存页面状态
  -->
  <div class="tabs-bar">
    <el-scrollbar class="tabs-scroll">
      <div class="tabs-list">
        <div
          v-for="tab in tabsStore.tabs"
          :key="tab.path"
          class="tab-item"
          :class="{ 'is-active': tab.path === activePath }"
          @click="onClick(tab)"
        >
          <span class="tab-dot" v-if="tab.affix"></span>
          <span class="tab-title">{{ tab.title }}</span>
          <el-icon
            v-if="!tab.affix"
            class="tab-close"
            @click.stop="onClose(tab)"
          >
            <Close />
          </el-icon>
        </div>
      </div>
    </el-scrollbar>

    <!-- 批量操作 -->
    <el-dropdown class="tabs-actions" trigger="click" @command="onCommand">
      <el-icon class="tabs-action-btn"><ArrowDown /></el-icon>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="close-others">关闭其他</el-dropdown-item>
          <el-dropdown-item command="close-all">关闭全部</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTabsStore } from '@/stores/tabs'

const route = useRoute()
const router = useRouter()
const tabsStore = useTabsStore()

const activePath = computed(() => route.path)

function onClick(tab: { path: string }) {
  if (tab.path !== route.path) {
    router.push(tab.path)
  }
}

function onClose(tab: { path: string }) {
  tabsStore.closeTab(tab.path)
  // 如果关闭的是当前激活标签，跳转到最后一个标签
  if (tab.path === route.path) {
    const last = tabsStore.tabs[tabsStore.tabs.length - 1]
    if (last) {
      router.push(last.path)
    } else {
      router.push('/dashboard')
    }
  }
}

function onCommand(cmd: string) {
  if (cmd === 'close-others') {
    tabsStore.closeOthers(route.path)
  } else if (cmd === 'close-all') {
    tabsStore.closeAll()
    // 关闭全部后回到首页
    const first = tabsStore.tabs[0]
    if (first && first.path !== route.path) {
      router.push(first.path)
    }
  }
}
</script>

<style scoped>
.tabs-bar {
  display: flex;
  align-items: center;
  height: 40px;
  background: #141926;
  border-bottom: 1px solid #1f2937;
  padding: 0 12px;
  gap: 8px;
}

.tabs-scroll {
  flex: 1;
}

.tabs-list {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12.5px;
  color: #9aa6bd;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  user-select: none;
}

.tab-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #e8ecf4;
}

.tab-item.is-active {
  background: rgba(74, 125, 224, 0.16);
  border-color: rgba(74, 125, 224, 0.35);
  color: #e8ecf4;
}

.tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4a7de0;
  flex-shrink: 0;
}

.tab-close {
  font-size: 12px;
  color: #5f6b82;
  transition: color 0.2s ease;
}

.tab-close:hover {
  color: #e8ecf4;
}

.tabs-actions {
  flex-shrink: 0;
}

.tabs-action-btn {
  font-size: 14px;
  color: #9aa6bd;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s ease, color 0.2s ease;
}

.tabs-action-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #e8ecf4;
}
</style>
