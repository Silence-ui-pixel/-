<template>
  <div class="login-page">
    <!-- 背景动画层 -->
    <BgAnimation />

    <!-- 自定义光标（Hello Kitty 风格） -->
    <CustomCursor />

    <!-- 主内容：登录卡片 + 卡通人物，横向布局 -->
    <div class="login-stage">
      <!-- 登录卡片 -->
      <div class="login-card">
        <div class="brand">
          <div class="brand-mark">W</div>
          <div>
            <div class="brand-title">仓储智能管理系统</div>
            <div class="brand-sub">WMS · AI Agent 工作台</div>
          </div>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          class="login-form"
          @submit.prevent="onSubmit"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              size="large"
              autocomplete="username"
              @focus="onInputFocus"
              @blur="onInputBlur"
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              size="large"
              show-password
              autocomplete="current-password"
              @focus="onInputFocus"
              @blur="onInputBlur"
              @keyup.enter="onSubmit"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loading"
            @click="onSubmit"
          >
            {{ loading ? '登录中…' : '登 录' }}
          </el-button>
        </el-form>

        <div class="tip">骨架阶段：输入任意用户名即可登录（假 token）</div>
      </div>

      <!-- 卡通人物（右侧，不挡表单） -->
      <div
        class="mascot-wrap"
        @mouseenter="mascotState = 'hover'"
        @mouseleave="onMascotLeave"
      >
        <Mascot :state="mascotState" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import BgAnimation from './components/BgAnimation.vue'
import CustomCursor from './components/CustomCursor.vue'
import Mascot, { type MascotState } from './components/Mascot.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// ---- 表单 ----
interface LoginForm {
  username: string
  password: string
}

const formRef = ref<FormInstance>()

const form = reactive<LoginForm>({
  username: 'admin',
  password: '',
})

const rules: FormRules<LoginForm> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const loading = ref(false)

// ---- 卡通人物状态 ----
// 优先级：loading > success > peeking > hover > idle
const isInputFocused = ref(false)
const hovered = ref(false)
const isSuccess = ref(false)

const mascotState = computed<MascotState>(() => {
  if (loading.value) return 'loading'
  if (isSuccess.value) return 'success'
  if (isInputFocused.value) return 'peeking'
  if (hovered.value) return 'hover'
  return 'idle'
})

function onInputFocus() {
  isInputFocused.value = true
}
function onInputBlur() {
  isInputFocused.value = false
}
function onMascotLeave() {
  hovered.value = false
}

// ---- 登录逻辑 ----
async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // TODO: 替换为真实登录接口
    await fakeLogin()
    auth.login(form.username.trim(), form.username.trim(), 'OPERATOR')
    isSuccess.value = true
    ElMessage.success('登录成功')
    // 停留片刻展示「比耶」动画，再跳转
    setTimeout(() => {
      const redirect = (route.query.redirect as string) || '/dashboard'
      router.push(redirect)
    }, 1200)
  } catch {
    ElMessage.error('登录失败，请重试')
    loading.value = false
  }
}

function fakeLogin(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 900))
}
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

// =============================================================================
// 舞台：卡片 + 卡通人物 横向布局
// =============================================================================
.login-stage {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 48px;
}

// =============================================================================
// 登录卡片
// =============================================================================
.login-card {
  width: 400px;
  max-width: calc(100vw - 40px);
  padding: 40px 36px 32px;
  border-radius: 18px;
  background: v.$card-bg;
  border: 1px solid v.$card-border;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  transition: box-shadow 0.5s v.$ease-out, border-color 0.5s v.$ease-out;

  // 入场淡入上浮 + 永久呼吸微动
  animation:
    card-enter 0.9s v.$ease-out both,
    card-float 6s ease-in-out 0.9s infinite;

  &:hover {
    border-color: rgba(120, 150, 220, 0.22);
    box-shadow: 0 14px 44px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(120, 150, 220, 0.08);
  }
}

// =============================================================================
// 品牌区
// =============================================================================
.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 32px;
}

.brand-mark {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: linear-gradient(135deg, v.$brand 0%, #355fae 100%);
  color: #fff;
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 6px 18px v.$brand-glow;
}

.brand-title {
  font-size: 17px;
  font-weight: 700;
  color: v.$text-primary;
  letter-spacing: 0.3px;
}

.brand-sub {
  font-size: 12px;
  color: v.$text-secondary;
  margin-top: 3px;
}

// =============================================================================
// 表单动效
// =============================================================================
.login-form {
  :deep(.el-form-item) {
    margin-bottom: 22px;
  }

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
    transition: box-shadow 0.35s v.$ease-out, transform 0.35s v.$ease-out;

    &::after {
      content: '';
      position: absolute;
      left: 0;
      bottom: 0;
      width: 0;
      height: 2px;
      border-radius: 2px;
      background: linear-gradient(90deg, v.$brand, v.$brand-hover);
      transition: width 0.45s v.$ease-out;
    }

    &:hover {
      box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.16) inset;
    }

    &.is-focus {
      transform: translateY(-1px);
      box-shadow: 0 0 0 1px rgba(120, 150, 220, 0.35) inset, 0 4px 16px rgba(74, 125, 224, 0.12);

      &::after {
        width: 100%;
      }
    }
  }

  :deep(.el-input__inner) {
    color: v.$text-primary;
  }
  :deep(.el-input__inner::placeholder) {
    color: v.$text-muted;
  }
  :deep(.el-input__prefix) {
    color: v.$text-secondary;
  }
}

// 登录按钮
.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, v.$brand 0%, #355fae 100%);
  font-size: 15px;
  letter-spacing: 2px;
  transition: box-shadow 0.4s v.$ease-out, filter 0.4s v.$ease-out, transform 0.15s v.$ease-out;

  &:hover {
    filter: brightness(1.08);
    box-shadow: 0 6px 20px v.$brand-glow;
  }

  &:active {
    transform: scale(0.97);
    box-shadow: 0 2px 8px rgba(74, 125, 224, 0.25);
  }

  &.is-loading {
    transform: none;
  }
}

.tip {
  margin-top: 22px;
  font-size: 12px;
  color: v.$text-muted;
  text-align: center;
}

:deep(.el-form-item__error) {
  transition: opacity 0.3s v.$ease-out;
}

// =============================================================================
// 卡通人物容器
// =============================================================================
.mascot-wrap {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

// =============================================================================
// keyframes
// =============================================================================
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(28px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes card-float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-6px); }
}

// =============================================================================
// 响应式：移动端卡通人物移到卡片上方并缩小
// =============================================================================
@media (max-width: 768px) {
  .login-stage {
    flex-direction: column;
    gap: 16px;
  }
  .mascot-wrap {
    order: -1; // 卡通人物放上面
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 32px 24px 26px;
    border-radius: 16px;
  }
  .brand-title {
    font-size: 16px;
  }
}

// =============================================================================
// 无障碍
// =============================================================================
@media (prefers-reduced-motion: reduce) {
  .login-card {
    animation: none !important;
  }
}
</style>
