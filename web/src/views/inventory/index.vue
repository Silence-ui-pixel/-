<template>
  <div>
    <el-page-header class="page-head" content="库存查询" />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="当前为骨架占位页：尚未接入 Mock 数据，S1-13 将在此实现查询逻辑。"
      class="mb"
    />
    <el-card shadow="never">
      <template #header><span class="block-title">查询条件（占位）</span></template>
      <el-form :inline="true">
        <el-form-item label="SKU">
          <el-input placeholder="SKU 编码" style="width: 180px" disabled />
        </el-form-item>
        <el-form-item label="库位">
          <el-input placeholder="库位编码" style="width: 180px" disabled />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" disabled>查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-empty description="等待 Mock server 就绪后填充数据" />
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.page-head {
  margin-bottom: 16px;
}
.mb {
  margin-bottom: 16px;
}
.block-title {
  font-size: 14px;
  font-weight: 600;
}
</style>
