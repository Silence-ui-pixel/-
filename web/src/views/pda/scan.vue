<script setup lang="ts">
// =============================================================================
// PDA 扫码作业页面（开发中占位）
// - 仅静态外壳，不实现扫码、不写业务逻辑、不调用后端接口
// =============================================================================
</script>

<template>
  <div class="pda-scan">
    <!-- 占位图标 -->
    <div class="scan-icon">
      <svg viewBox="0 0 24 24" width="56" height="56" fill="none" aria-hidden="true">
        <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M7 12h10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
      </svg>
    </div>

    <p class="scan-text">PDA扫码作业页面（开发中占位）</p>
    <p class="scan-sub">扫码、库位校验等业务能力将在后续版本接入</p>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/variables' as *;

.pda-scan {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 40px 24px;
  text-align: center;
}

.scan-icon {
  color: $text-muted;
  margin-bottom: 20px;
}

.scan-text {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: $text-primary;
}

.scan-sub {
  margin: 12px 0 0;
  font-size: 13px;
  color: $text-muted;
}
</style>
