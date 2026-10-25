<template>
  <div class="forbidden-page">
    <div class="forbidden-code">403</div>
    <div class="forbidden-title">无权限访问</div>
    <div class="forbidden-desc">您没有权限访问该页面，请联系管理员开通权限</div>
    <el-button type="primary" @click="goHome">返回工作台</el-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/dashboard')
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.forbidden-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  background: v.$bg-deep;
}

.forbidden-code {
  font-size: 72px;
  font-weight: 700;
  color: v.$brand;
  letter-spacing: 4px;
  line-height: 1;
}

.forbidden-title {
  font-size: 20px;
  font-weight: 600;
  color: v.$text-primary;
}

.forbidden-desc {
  font-size: 13px;
  color: v.$text-muted;
  margin-bottom: 8px;
}
</style>
