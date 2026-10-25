// =============================================================================
// MSW Service Worker 实例（浏览器端）
// 仅在开发环境 + VITE_USE_MOCK=true 时由 main.ts 动态加载启动。
// =============================================================================
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
