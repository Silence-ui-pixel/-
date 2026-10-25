import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserRole } from '@/types/models'
import { client } from '@/api/client'

const TOKEN_KEY = 'wms_token'
const USER_KEY = 'wms_user'

export interface AuthUser {
  username: string
  displayName: string
  role: UserRole
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<AuthUser | null>(readUser())

  /**
   * 从 localStorage 读取并解析用户信息
   * 读取失败（数据损坏 / 无数据）时返回 null，由调用方按未登录处理。
   */
  function readUser(): AuthUser | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as AuthUser
    } catch {
      return null
    }
  }

  const isLoggedIn = computed(() => !!token.value)

  /**
   * 当前用户角色（未登录时为 null）
   * ⚠️ 前端权限仅做「体验拦截」：用于隐藏菜单 / 控制按钮显隐 / 拦截无权限跳转。
   *    最终鉴权由后端 A 兜底——任何写操作、敏感数据读取，后端都会再次校验角色，
   *    前端角色信息可被篡改，不能作为安全依据。
   */
  const role = computed<UserRole | null>(() => user.value?.role ?? null)

  /** 判断当前用户是否属于给定角色集合（未登录恒为 false） */
  function hasRole(roles: UserRole[]): boolean {
    if (!role.value) return false
    return roles.includes(role.value)
  }

  /**
   * 真实登录：POST /auth/login 换 JWT → GET /users/me 取用户信息（含角色）。
   * - 失败时 client 已把后端错误转成 ApiError（中文 message），由调用方 catch 展示；
   * - 角色仅用于前端体验拦截（菜单/按钮），最终鉴权由后端兜底。
   */
  async function login(username: string, password: string): Promise<void> {
    const { data } = await client.POST('/auth/login', {
      body: { username, password },
    })
    if (!data?.access_token) throw new Error('登录失败：未返回 token')

    token.value = data.access_token
    localStorage.setItem(TOKEN_KEY, data.access_token)

    // 拉取当前用户：角色决定菜单与按钮可见性
    const { data: me } = await client.GET('/users/me')
    if (me) {
      user.value = {
        username: me.username ?? username,
        displayName: me.display_name ?? username,
        role: (me.role as UserRole) ?? 'VIEWER',
      }
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, role, isLoggedIn, hasRole, login, logout }
})
