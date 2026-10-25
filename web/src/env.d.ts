/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** 是否启用 MSW Mock（'true' 拦截请求返回假数据） */
  readonly VITE_USE_MOCK?: string
  /** API 基地址（Mock 关闭时生效） */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
