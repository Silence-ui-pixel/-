<template>
  <!--
    自定义可爱光标（Hello Kitty 风格）
    - 默认：Hello Kitty 基础头像光标
    - 可交互元素（按钮/输入框/链接）：Hello Kitty 举手样式光标
    - 降级：浏览器不支持自定义 cursor 时，CSS 会自动回退到原生光标
    - 纯 CSS 实现，通过全局 class 切换 cursor 图片，不影响输入和点击
  -->
  <div class="custom-cursor-root" aria-hidden="true"></div>
</template>

<script setup lang="ts">
// 光标通过 CSS（:root / a、button、input）全局设置，见下方 style。
// 此处无运行时逻辑，组件仅作为「光标配置」的挂载点与文档说明。
// 若未来需要动态切换，可在 onMounted 里向 document.body 添加/移除 class。
</script>

<style lang="scss">
// =============================================================================
// 自定义光标：使用内联 SVG（data URI）作为 cursor 图片
// =============================================================================
//
// 【资源说明】
// 光标图片是内联 SVG 的 data URI，不依赖外部文件，直接内嵌在 CSS 里。
// 如果你有自己的 PNG 光标素材，替换方式：
//   把下面 url("data:image/svg+xml,...") 换成 url("/cursors/kitty.png"),
//   并把图片放到 public/cursors/ 目录即可。
//
// 【降级说明】
// cursor 属性写两个值：第一个是自定义图片，第二个是 fallback 关键字。
// 当浏览器无法加载自定义图片（不支持 SVG cursor / 路径错误）时，
// 会自动使用后面的 fallback（pointer / auto / default），不影响交互。

:root {
  // 默认光标：Hello Kitty 基础头像（圆脸 + 蝴蝶结 + 胡须）
  --cursor-default: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%23ffffff' stroke='%239a8a95' stroke-width='1.5'/><circle cx='10' cy='11' r='3' fill='%23f2b8c6'/><circle cx='22' cy='11' r='3' fill='%23f2b8c6'/><circle cx='8' cy='16' r='1.6' fill='%23222'/><circle cx='24' cy='16' r='1.6' fill='%23222'/><ellipse cx='16' cy='21' rx='2.2' ry='1.6' fill='%23f2b8c6'/><line x1='3' y1='20' x2='10' y2='19' stroke='%239a8a95' stroke-width='1'/><line x1='3' y1='23' x2='10' y2='22' stroke='%239a8a95' stroke-width='1'/><line x1='29' y1='20' x2='22' y2='19' stroke='%239a8a95' stroke-width='1'/><line x1='29' y1='23' x2='22' y2='22' stroke='%239a8a95' stroke-width='1'/></svg>"), auto;

  // 可交互元素光标：Hello Kitty 举手（卖萌打招呼）
  --cursor-pointer: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%23ffffff' stroke='%239a8a95' stroke-width='1.5'/><circle cx='10' cy='11' r='3' fill='%23f2b8c6'/><circle cx='22' cy='11' r='3' fill='%23f2b8c6'/><circle cx='8' cy='16' r='1.6' fill='%23222'/><circle cx='24' cy='16' r='1.6' fill='%23222'/><ellipse cx='16' cy='21' rx='2.2' ry='1.6' fill='%23f2b8c6'/><line x1='16' y1='8' x2='22' y2='2' stroke='%23f2b8c6' stroke-width='2.5' stroke-linecap='round'/><circle cx='22' cy='1.5' r='3.5' fill='%23f2b8c6'/><line x1='3' y1='20' x2='10' y2='19' stroke='%239a8a95' stroke-width='1'/><line x1='29' y1='20' x2='22' y2='19' stroke='%239a8a95' stroke-width='1'/></svg>"), pointer;
}

// 全局默认光标
body {
  cursor: var(--cursor-default);
}

// 可交互元素：切换为举手光标
a,
button,
.el-button,
.el-input__inner,
input,
textarea,
select,
.el-input__wrapper,
[role='button'],
[tabindex]:not([tabindex='-1']) {
  cursor: var(--cursor-pointer);
}

// 输入框内仍保持文本光标，避免影响打字体验
input[type='text'],
input[type='password'],
input[type='email'],
textarea {
  cursor: text;
}

// 禁用态回退默认
button:disabled,
.el-button.is-disabled {
  cursor: var(--cursor-default);
}
</style>
