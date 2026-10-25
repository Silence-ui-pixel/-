import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserRole } from '@/types/models'

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

  // 假登录：不接后端，直接写入本地 token 与用户信息
  function login(username: string, displayName: string, role: UserRole) {
    token.value = `fake-token-${Date.now()}`
    user.value = { username, displayName, role }
    localStorage.setItem(TOKEN_KEY, token.value)
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, role, isLoggedIn, hasRole, login, logout }
})
