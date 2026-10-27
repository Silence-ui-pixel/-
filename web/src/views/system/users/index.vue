<template>
  <div class="user-manage">
    <!-- ========== 统计条 ========== -->
    <section class="panel stats">
      <div class="stat-total">
        <span class="stat-num">{{ total }}</span>
        <span class="stat-label">个用户</span>
      </div>
      <div v-for="s in roleStats" :key="s.role" class="stat-item">
        <el-tag :type="ROLE_TAG[s.role]" size="small" effect="dark">{{ ROLE_TEXT[s.role] }}</el-tag>
        <span class="stat-count">{{ s.count }}</span>
      </div>
    </section>

    <!-- ========== 筛选 ========== -->
    <section class="panel toolbar">
      <el-form :inline="true" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="搜索">
          <el-input
            v-model="filters.keyword"
            placeholder="用户名 / 姓名"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="(t, k) in ROLE_TEXT" :key="k" :label="t" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <!-- ========== 列表 ========== -->
    <section class="panel">
      <div class="panel-title">
        <span>用户列表</span>
        <span class="panel-hint">本期只读 · 契约未开放用户增删改</span>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="暂无用户"
        :row-key="(r: UserItem) => r.id!"
        :row-class-name="rowClassName"
        class="data-table"
      >
        <el-table-column prop="username" label="用户名" min-width="150">
          <template #default="{ row }">
            <span class="username">{{ row.username }}</span>
            <el-tag v-if="row.username === auth.user?.username" size="small" class="me-tag">当前登录</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="display_name" label="姓名" min-width="130">
          <template #default="{ row }">{{ row.display_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="roleTag(row.role)" size="small">{{ roleText(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可访问范围" min-width="280">
          <template #default="{ row }">
            <span class="scope-text">{{ roleScope(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <span :class="row.status === 1 ? 'status-on' : 'status-off'">
              {{ row.status === 1 ? '启用' : '停用' }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadData"
        />
      </div>
    </section>

    <!-- ========== 角色权限说明（只读页面的补充价值） ========== -->
    <section class="panel">
      <div class="panel-title">
        <span>角色权限说明</span>
        <span class="panel-hint">由后端接口鉴权，前端仅做菜单与路由可见性收敛</span>
      </div>
      <div class="role-legend">
        <div v-for="role in roleOrder" :key="role" class="legend-item">
          <div class="legend-head">
            <el-tag :type="ROLE_TAG[role]" size="small" effect="dark">{{ ROLE_TEXT[role] }}</el-tag>
          </div>
          <div class="legend-body">{{ ROLE_SCOPE[role] }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
// =============================================================================
// 用户角色（只读）
// - 接口：GET /users（分页，契约要求 MANAGER/ADMIN，返回不含 password_hash）
// - 筛选：keyword（username/display_name 模糊） + role（精确）
// - 契约未开放用户增删改 / 改密 / 改角色，页面不提供任何编辑入口
// - 角色实际能做什么由后端鉴权决定，前端只影响菜单与路由可见性
// =============================================================================
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { client, ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { components, paths } from '@/api/schema'

type UserItem = components['schemas']['UserListItem']
type UserQuery = NonNullable<paths['/users']['get']['parameters']['query']>
type Role = NonNullable<UserItem['role']>

const auth = useAuthStore()

const ROLE_TEXT: Record<Role, string> = {
  ADMIN: '系统管理员',
  MANAGER: '仓管主管',
  OPERATOR: '操作员',
  VIEWER: '只读用户',
}

const ROLE_TAG: Record<Role, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
  ADMIN: 'danger',
  MANAGER: 'warning',
  OPERATOR: 'primary',
  VIEWER: 'info',
}

/** 各角色可访问范围（说明性文案，鉴权以后端为准） */
const ROLE_SCOPE: Record<Role, string> = {
  ADMIN: '全部功能：用户管理、商品 / 库位主数据、库存对账、出入库作业',
  MANAGER: '除用户管理外的全部：商品 / 库位主数据、库存对账、出入库作业',
  OPERATOR: '作业执行：收货、上架、拣货、发运、库存查询与流水',
  VIEWER: '只读：库存查询、库存流水（无任何写操作入口）',
}

const roleOrder: Role[] = ['ADMIN', 'MANAGER', 'OPERATOR', 'VIEWER']

const loading = ref(false)
const rows = ref<UserItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({
  keyword: '',
  role: '' as Role | '',
})

/** 当前页的角色分布（基于已加载数据） */
const roleStats = computed(() => {
  const roleMap = new Map<Role, number>()
  for (const r of rows.value) {
    if (!r.role) continue
    roleMap.set(r.role, (roleMap.get(r.role) ?? 0) + 1)
  }
  return roleOrder.filter((r) => roleMap.has(r)).map((role) => ({ role, count: roleMap.get(role)! }))
})

function rowClassName({ row }: { row: UserItem }) {
  return row.username === auth.user?.username ? 'row-me' : ''
}

/** 表格插槽的 row 为 any，用这三个 helper 收口类型（未知角色回退原值/中性色） */
function roleText(role: unknown): string {
  return ROLE_TEXT[role as Role] ?? String(role ?? '—')
}

function roleTag(role: unknown): 'primary' | 'success' | 'info' | 'warning' | 'danger' {
  return ROLE_TAG[role as Role] ?? 'info'
}

function roleScope(role: unknown): string {
  return ROLE_SCOPE[role as Role] ?? '—'
}

async function loadData() {
  loading.value = true
  try {
    const query: UserQuery = { page: page.value, page_size: pageSize.value }
    if (filters.keyword.trim()) query.keyword = filters.keyword.trim()
    if (filters.role) query.role = filters.role

    const { data } = await client.GET('/users', { params: { query } })
    rows.value = data?.items ?? []
    total.value = data?.meta?.total ?? rows.value.length
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '加载用户列表失败')
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

function handleReset() {
  filters.keyword = ''
  filters.role = ''
  page.value = 1
  loadData()
}

onMounted(loadData)
</script>

<style scoped lang="scss">
@use '@/styles/variables' as v;

.user-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  background: rgba(24, 29, 42, 0.72);
  border: 1px solid v.$card-border;
  border-radius: 12px;
  padding: 16px 18px;
}

/* ---------- 统计条 ---------- */
.stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.stat-total {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding-right: 20px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: v.$text-primary;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: v.$text-muted;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 7px;
}

.stat-count {
  font-size: 15px;
  font-weight: 600;
  color: v.$text-primary;
}

/* ---------- 筛选 / 列表 ---------- */
.toolbar {
  padding-bottom: 4px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 0;
}

.panel-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: v.$text-primary;
}

.panel-hint {
  font-size: 12px;
  font-weight: 400;
  color: v.$text-muted;
}

.username {
  font-family: 'JetBrains Mono', Consolas, monospace;
  color: v.$text-primary;
}

.me-tag {
  margin-left: 8px;
}

.scope-text {
  font-size: 12px;
  line-height: 1.5;
  color: v.$text-muted;
}

.status-on {
  color: #6fd39b;
  font-size: 13px;
}

.status-off {
  color: v.$text-muted;
  font-size: 13px;
}

:deep(.row-me) {
  background: rgba(64, 158, 255, 0.08);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* ---------- 角色权限说明 ---------- */
.role-legend {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.legend-item {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.legend-head {
  margin-bottom: 8px;
}

.legend-body {
  font-size: 12px;
  line-height: 1.65;
  color: v.$text-muted;
}
</style>
