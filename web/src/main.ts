import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './styles/index.css'

/**
 * 启动引导：开发环境且开启 Mock 时，先启动 MSW Service Worker 再挂载应用，
 * 确保首个请求即被 mock 拦截。
 */
async function bootstrap() {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === 'true') {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  const app = createApp(App)

  // 全局注册 Element Plus 图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.use(createPinia())
  app.use(router)
  app.use(ElementPlus)

  app.mount('#app')
}

bootstrap()
