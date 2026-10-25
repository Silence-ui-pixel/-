<template>
  <!--
    登录页背景动画层（纯 CSS 实现，无 Canvas，保证性能）
    构成：
      1. 多层柔和渐变，缓慢流动（呼吸感）
      2. 细碎光点粒子，缓慢漂浮淡入淡出（数量少、不密集）
      3. 微弱光带，丝滑游走（透明度极低，作为底层烘托）
    说明：开启 prefers-reduced-motion 时，所有动画自动关闭。
  -->
  <div class="bg-layer" aria-hidden="true">
    <!-- 渐变层：三个错位的径向渐变，各自缓慢位移 -->
    <div class="bg-blob bg-blob--1"></div>
    <div class="bg-blob bg-blob--2"></div>
    <div class="bg-blob bg-blob--3"></div>

    <!-- 光带：一条极淡的斜向光带，丝滑游走 -->
    <div class="bg-lightbar"></div>

    <!-- 粒子：少量光点，漂浮 + 淡入淡出 -->
    <div class="particle particle--1"></div>
    <div class="particle particle--2"></div>
    <div class="particle particle--3"></div>
    <div class="particle particle--4"></div>
    <div class="particle particle--5"></div>
    <div class="particle particle--6"></div>

    <!-- 底部暗角，压低整体亮度，避免抢表单重心 -->
    <div class="bg-vignette"></div>
  </div>
</template>

<script setup lang="ts">
// 纯展示组件，无逻辑
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background: v.$bg-deep;
  pointer-events: none; // 不拦截鼠标事件
}

// ---- 渐变光斑 ----
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.5;
  will-change: transform;
}

.bg-blob--1 {
  width: 60vw;
  height: 60vw;
  left: -15vw;
  top: -20vw;
  background: radial-gradient(circle, v.$bg-grad-1 0%, transparent 70%);
  animation: drift-1 v.$dur-bg-drift ease-in-out infinite alternate;
}

.bg-blob--2 {
  width: 55vw;
  height: 55vw;
  right: -18vw;
  top: 10vh;
  background: radial-gradient(circle, v.$bg-grad-2 0%, transparent 70%);
  animation: drift-2 (v.$dur-bg-drift * 1.3) ease-in-out infinite alternate;
}

.bg-blob--3 {
  width: 50vw;
  height: 50vw;
  left: 25vw;
  bottom: -25vw;
  background: radial-gradient(circle, v.$bg-grad-3 0%, transparent 70%);
  animation: drift-3 (v.$dur-bg-drift * 1.6) ease-in-out infinite alternate;
}

// ---- 光带 ----
.bg-lightbar {
  position: absolute;
  top: -20%;
  left: -30%;
  width: 45%;
  height: 140%;
  background: linear-gradient(
    100deg,
    transparent 0%,
    rgba(120, 150, 220, 0.06) 45%,
    rgba(140, 170, 235, 0.1) 50%,
    rgba(120, 150, 220, 0.06) 55%,
    transparent 100%
  );
  filter: blur(40px);
  transform: rotate(20deg);
  animation: lightbar-sweep 18s ease-in-out infinite;
}

// ---- 粒子 ----
.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(180, 200, 240, 0.6);
  opacity: 0;
  will-change: transform, opacity;
}

@mixin particle-float($dur, $delay, $dx, $dy) {
  animation: particle-float $dur ease-in-out $delay infinite;
  // 用 CSS 变量记录漂浮方向，在 keyframes 里引用
  --dx: #{$dx};
  --dy: #{$dy};
}

.particle--1 { left: 12%; top: 30%; @include particle-float(9s, 0s, 30px, -40px); }
.particle--2 { left: 22%; top: 68%; @include particle-float(11s, 1.2s, -36px, -30px); }
.particle--3 { left: 78%; top: 22%; @include particle-float(10s, 0.6s, -28px, 34px); }
.particle--4 { left: 85%; top: 60%; @include particle-float(12s, 2s, 24px, -28px); }
.particle--5 { left: 48%; top: 14%; @include particle-float(13s, 3s, 20px, 26px); }
.particle--6 { left: 62%; top: 82%; @include particle-float(10s, 1.6s, -22px, -24px); }

// ---- 底部暗角 ----
.bg-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at center,
    transparent 40%,
    rgba(5, 7, 11, 0.55) 100%
  );
}

// =============================================================================
// keyframes
// =============================================================================

// 渐变光斑：缓慢平移 + 轻微缩放，制造「流动 + 呼吸」感
@keyframes drift-1 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(8vw, 6vh) scale(1.15); }
}
@keyframes drift-2 {
  from { transform: translate(0, 0) scale(1.1); }
  to   { transform: translate(-6vw, -8vh) scale(1); }
}
@keyframes drift-3 {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(5vw, -6vh) scale(1.2); }
}

// 光带：横向丝滑扫过
@keyframes lightbar-sweep {
  0%   { transform: translateX(-10%) rotate(20deg); opacity: 0; }
  20%  { opacity: 1; }
  50%  { transform: translateX(120%) rotate(20deg); opacity: 0.8; }
  80%  { opacity: 1; }
  100% { transform: translateX(240%) rotate(20deg); opacity: 0; }
}

// 粒子：按各自方向漂浮 + 淡入淡出
@keyframes particle-float {
  0%   { transform: translate(0, 0); opacity: 0; }
  25%  { opacity: 0.7; }
  50%  { transform: translate(var(--dx), var(--dy)); opacity: 0.35; }
  75%  { opacity: 0.7; }
  100% { transform: translate(0, 0); opacity: 0; }
}

// =============================================================================
// 无障碍：系统开启「减弱动态效果」时，关闭所有背景动画
// =============================================================================
@media (prefers-reduced-motion: reduce) {
  .bg-blob,
  .bg-lightbar,
  .particle {
    animation: none !important;
  }
  .particle {
    opacity: 0; // 静止状态下隐藏粒子，保持干净
  }
}
</style>
