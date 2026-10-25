<template>
  <div class="placeholder-page">
    <div class="placeholder-icon">
      <el-icon><Tickets /></el-icon>
    </div>
    <div class="placeholder-title">入库单页面（开发中占位）</div>
    <div class="placeholder-desc">业务功能将在后续迭代接入，当前为静态占位</div>
  </div>
</template>

<script setup lang="ts">
// 占位页：不写业务逻辑
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.placeholder-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 12px;
}

.placeholder-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(74, 125, 224, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: v.$brand;
}

.placeholder-title {
  font-size: 16px;
  font-weight: 600;
  color: v.$text-primary;
}

.placeholder-desc {
  font-size: 13px;
  color: v.$text-muted;
}
</style>
