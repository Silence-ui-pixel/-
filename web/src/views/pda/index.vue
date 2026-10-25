<template>
  <div class="pda-page">
    <el-page-header class="page-head" content="PDA 扫码" />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="PDA 扫码页原型占位：S1-14 将实现扫码输入框自动聚焦、软键盘适配。"
      class="mb"
    />
    <el-card shadow="never">
      <template #header><span class="block-title">扫码区（占位）</span></template>
      <el-input size="large" placeholder="扫码枪 / 手动输入条码" disabled>
        <template #prefix><el-icon><FullScreen /></el-icon></template>
      </el-input>
    </el-card>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.pda-page {
  max-width: 720px;
}
.page-head {
  margin-bottom: 16px;
}
.mb {
  margin-bottom: 16px;
}
.block-title {
  font-size: 14px;
  font-weight: 600;
}
</style>
