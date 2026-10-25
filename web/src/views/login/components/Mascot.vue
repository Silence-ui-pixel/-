<template>
  <!--
    Q 版卡通人物（软萌卖萌风）
    - 纯内联 SVG 手绘，无外部图片依赖，体积小
    - 通过 props 传入状态，CSS 类控制不同动作
    - 状态机：idle（静止）/ hover（卖萌）/ peeking（偷看输入）/ loading（加油）/ success（比耶）
  -->
  <div class="mascot" :class="`mascot--${state}`" aria-hidden="true">
    <svg
      viewBox="0 0 200 220"
      xmlns="http://www.w3.org/2000/svg"
      class="mascot-svg"
    >
      <!-- ===== 身体 ===== -->
      <!-- 身体（圆润 Q 版） -->
      <ellipse cx="100" cy="180" rx="52" ry="40" fill="#7d8bb0" />
      <!-- 小肚子 -->
      <ellipse cx="100" cy="186" rx="30" ry="26" fill="#a8b4d4" />

      <!-- ===== 头 ===== -->
      <!-- 脑袋 -->
      <circle cx="100" cy="95" r="62" fill="#b9c4de" />

      <!-- 耳朵 / 呆毛 -->
      <path d="M100 33 Q104 18 112 24 Q108 34 100 38 Z" fill="#b9c4de" />

      <!-- ===== 眼睛（支持眨眼，用 scaleY 动画） ===== -->
      <g class="eyes">
        <ellipse cx="78" cy="92" rx="7" ry="9" fill="#3a4358" />
        <ellipse cx="122" cy="92" rx="7" ry="9" fill="#3a4358" />
        <!-- 高光 -->
        <circle cx="80.5" cy="89" r="2.5" fill="#fff" />
        <circle cx="124.5" cy="89" r="2.5" fill="#fff" />
      </g>

      <!-- ===== 腮红 ===== -->
      <ellipse cx="64" cy="108" rx="10" ry="6" fill="#e8a7b8" opacity="0.7" />
      <ellipse cx="136" cy="108" rx="10" ry="6" fill="#e8a7b8" opacity="0.7" />

      <!-- ===== 嘴巴（状态切换） ===== -->
      <!-- 微笑（默认 / idle） -->
      <path class="mouth mouth--smile" d="M86 112 Q100 126 114 112" fill="none" stroke="#3a4358" stroke-width="3.5" stroke-linecap="round" />
      <!-- 开心张嘴笑（success） -->
      <path class="mouth mouth--happy" d="M84 110 Q100 134 116 110 Z" fill="#8a5a6a" />

      <!-- ===== 手臂 ===== -->
      <!-- 左臂（默认垂下） -->
      <path class="arm arm--left" d="M52 168 Q36 180 42 198" fill="none" stroke="#7d8bb0" stroke-width="14" stroke-linecap="round" />
      <!-- 右臂（默认垂下） -->
      <path class="arm arm--right" d="M148 168 Q164 180 158 198" fill="none" stroke="#7d8bb0" stroke-width="14" stroke-linecap="round" />

      <!-- 挥手的手臂（hover 状态时替换右侧手臂，抬手挥动） -->
      <g class="arm arm--wave">
        <path d="M148 168 Q176 140 172 118" fill="none" stroke="#7d8bb0" stroke-width="14" stroke-linecap="round" />
        <!-- 小手 -->
        <circle cx="172" cy="116" r="10" fill="#b9c4de" />
      </g>

      <!-- 比耶的手（success 状态） -->
      <g class="arm arm--victory">
        <path d="M148 168 Q168 136 168 108" fill="none" stroke="#7d8bb0" stroke-width="14" stroke-linecap="round" />
        <circle cx="168" cy="104" r="9" fill="#b9c4de" />
        <!-- 比耶的两根手指 -->
        <rect x="164" y="82" width="5" height="16" rx="2.5" fill="#b9c4de" />
        <rect x="172" y="78" width="5" height="20" rx="2.5" fill="#b9c4de" />
      </g>

      <!-- ===== 脚 ===== -->
      <ellipse cx="78" cy="212" rx="16" ry="8" fill="#7d8bb0" />
      <ellipse cx="122" cy="212" rx="16" ry="8" fill="#7d8bb0" />
    </svg>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'

// 卡通人物状态类型
export type MascotState = 'idle' | 'hover' | 'peeking' | 'loading' | 'success'

const props = defineProps({
  state: {
    type: String as PropType<MascotState>,
    default: 'idle',
  },
})

// props 仅为声明，避免未使用告警
void props
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.mascot {
  position: relative;
  width: 150px;
  height: 165px;
  cursor: default;
  // 整体柔和过渡
  transition: transform 0.4s v.$ease-out;
  transform-origin: center bottom;
}

.mascot-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

// =============================================================================
// 状态：idle（静止）—— 轻微晃脑袋 + 眨眼睛 + 小幅摇摆身体
// =============================================================================
.mascot--idle {
  .mascot-svg {
    animation: idle-sway 5s ease-in-out infinite;
  }
  .eyes {
    transform-origin: center;
    animation: blink 4.5s infinite;
  }
}

// 轻微摇摆（旋转极小幅，几乎察觉不到）
@keyframes idle-sway {
  0%, 100% { transform: rotate(0deg); }
  50%      { transform: rotate(2.2deg); }
}

// 眨眼：大部分时间睁开，瞬间闭合
@keyframes blink {
  0%, 92%, 100% { transform: scaleY(1); }
  94%, 96%      { transform: scaleY(0.1); }
}

// =============================================================================
// 状态：hover（卖萌）—— 歪头 + 挥手 + 蹦一下
// =============================================================================
.mascot--hover {
  .mascot-svg {
    animation: hover-bounce 0.9s v.$ease-out infinite alternate;
  }
  .arm--left,
  .arm--right {
    opacity: 0;
  }
  .arm--wave {
    opacity: 1;
    animation: wave 0.6s ease-in-out infinite alternate;
  }
}

// 蹦一下：轻微上移 + 歪头
@keyframes hover-bounce {
  from { transform: translateY(0) rotate(-6deg); }
  to   { transform: translateY(-12px) rotate(-6deg); }
}

// 挥手
@keyframes wave {
  from { transform: rotate(-12deg); }
  to   { transform: rotate(14deg); }
}

// =============================================================================
// 状态：peeking（偷看输入）—— 身体前倾 + 探头
// =============================================================================
.mascot--peeking {
  .mascot-svg {
    animation: peek 3s ease-in-out infinite;
  }
  .eyes {
    animation: peek-blink 2.8s infinite;
  }
}

@keyframes peek {
  0%, 100% { transform: translateX(0) rotate(0deg); }
  30%      { transform: translateX(-10px) rotate(-4deg); }
  60%      { transform: translateX(2px) rotate(2deg); }
}

@keyframes peek-blink {
  0%, 88%, 100% { transform: scaleY(1); }
  90%, 94%      { transform: scaleY(0.15); }
}

// =============================================================================
// 状态：loading（加油等待）—— 小幅蹦跳打气
// =============================================================================
.mascot--loading {
  .mascot-svg {
    animation: loading-hop 0.7s ease-in-out infinite alternate;
  }
  .arm--left,
  .arm--right {
    opacity: 0;
  }
  .arm--wave {
    opacity: 1;
    animation: wave 0.5s ease-in-out infinite alternate;
  }
}

@keyframes loading-hop {
  from { transform: translateY(0); }
  to   { transform: translateY(-10px); }
}

// =============================================================================
// 状态：success（开心比耶）—— 蹦起来 + 咧嘴笑 + 比耶手
// =============================================================================
.mascot--success {
  .mascot-svg {
    animation: success-jump 0.8s v.$ease-out 2;
  }
  .mouth--smile {
    opacity: 0;
  }
  .mouth--happy {
    opacity: 1;
  }
  .arm--left,
  .arm--right {
    opacity: 0;
  }
  .arm--victory {
    opacity: 1;
  }
}

@keyframes success-jump {
  0%   { transform: translateY(0); }
  40%  { transform: translateY(-22px); }
  70%  { transform: translateY(0); }
  85%  { transform: translateY(-8px); }
  100% { transform: translateY(0); }
}

// =============================================================================
// 手臂 / 嘴巴的默认显隐
// =============================================================================
.arm--wave,
.arm--victory {
  opacity: 0;
  transform-origin: center;
}
.arm--left,
.arm--right {
  transition: opacity 0.3s v.$ease-out;
}
.mouth--happy {
  opacity: 0;
  transition: opacity 0.3s v.$ease-out;
}
.mouth--smile {
  transition: opacity 0.3s v.$ease-out;
}

// =============================================================================
// 无障碍：减弱动画时，卡通人物保持静止微笑
// =============================================================================
@media (prefers-reduced-motion: reduce) {
  .mascot-svg,
  .eyes,
  .arm--wave,
  .arm--victory {
    animation: none !important;
  }
}

// =============================================================================
// 响应式：小屏时缩小
// =============================================================================
@media (max-width: 768px) {
  .mascot {
    width: 100px;
    height: 110px;
  }
}
</style>
