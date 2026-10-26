<template>
  <!-- 库存模块父组件：仅承载子路由出口，无自身内容 -->
  <router-view />
</template>

<script setup lang="ts">
// 分组父组件：redirect 到子路由，本身只做 router-view 出口。
//
// 历史坑：这里原本是 42 行的「骨架占位页」（禁用输入框 + "等待 Mock 就绪" 提示）。
// 后来真页面建在 inventory/query 和 inventory/txn 下，但父组件忘了改成出口，
// 结果 /inventory/query 匹配到「父组件 + 子组件」，而父组件里没有 <router-view>，
// 子组件渲染不出来 —— 点「库存查询」看到的永远是那个占位页。
// 写法与 inbound / outbound / system 的 index.vue 保持一致。
</script>
