<template>
  <div class="page-access">
    <div class="page-header">
      <h1 class="page-title">页面访问管理</h1>
      <div>
        <el-button @click="loadConfigs">重置</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>各角色可见页面配置</span>
          <span class="header-tip">关闭后对应角色的侧边栏菜单将隐藏该页面，直接访问将被重定向到数据仪表盘；「数据仪表盘」始终可见</span>
        </div>
      </template>

      <el-table :data="tableData" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="页面名称" min-width="140" />
        <el-table-column prop="path" label="页面路径" min-width="140">
          <template #default="{ row }">
            <el-text type="info" size="small">{{ row.path }}</el-text>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.inMenu ? 'primary' : 'info'" size="small" effect="plain">
              {{ row.inMenu ? '菜单页面' : '功能页面' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="仅管理员可见" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.adminOnly" type="warning" size="small" effect="plain">是</el-tag>
            <el-text v-else type="info">否</el-text>
          </template>
        </el-table-column>
        <el-table-column label="管理员" width="110" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.admin" />
          </template>
        </el-table-column>
        <el-table-column label="班主任" width="110" align="center">
          <template #default="{ row }">
            <el-switch v-if="!row.adminOnly" v-model="row.class_teacher" />
            <el-tooltip v-else content="该页面仅管理员可访问" placement="top">
              <el-icon class="no-access-icon"><CircleClose /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="任课教师" width="110" align="center">
          <template #default="{ row }">
            <el-switch v-if="!row.adminOnly" v-model="row.teacher" />
            <el-tooltip v-else content="该页面仅管理员可访问" placement="top">
              <el-icon class="no-access-icon"><CircleClose /></el-icon>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleClose } from '@element-plus/icons-vue'
import api from '@/api'
import { PAGE_REGISTRY, ROLE_LABELS } from '@/config/pages'

const loading = ref(false)
const saving = ref(false)
const tableData = ref([])

const buildDefaultRows = () =>
  PAGE_REGISTRY.map(p => ({
    path: p.path,
    title: p.title,
    inMenu: p.inMenu,
    adminOnly: p.adminOnly,
    admin: true,
    class_teacher: true,
    teacher: true
  }))

const loadConfigs = async () => {
  loading.value = true
  try {
    const rows = buildDefaultRows()
    try {
      const configs = (await api.pageAccess.getAll()) || []
      const byKey = new Map(configs.map(c => [`${c.role}|${c.page_path}`, c.is_visible]))
      for (const row of rows) {
        for (const role of Object.keys(ROLE_LABELS)) {
          const key = `${role}|${row.path}`
          if (byKey.has(key)) row[role] = byKey.get(key)
        }
      }
    } catch (e) {
      // 读取失败时保持默认全部可见
      console.error('读取页面访问配置失败:', e)
    }
    tableData.value = rows
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const configs = []
    for (const row of tableData.value) {
      for (const role of Object.keys(ROLE_LABELS)) {
        // adminOnly 页面对非管理员角色本身不可见，无需下发配置
        if (row.adminOnly && role !== 'admin') continue
        configs.push({ role, page_path: row.path, is_visible: !!row[role] })
      }
    }
    await api.pageAccess.batchUpdate({ configs })
    ElMessage.success('页面访问配置已保存')
  } catch (e) {
    console.error('保存页面访问配置失败:', e)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadConfigs)
</script>

<style scoped>
.page-access {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 22px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-tip {
  font-size: 12px;
  color: #909399;
}

.no-access-icon {
  color: #c0c4cc;
  font-size: 18px;
}
</style>
