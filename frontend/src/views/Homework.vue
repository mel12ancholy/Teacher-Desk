<template>
  <div class="homework-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span><el-icon><Document /></el-icon> 作业管理</span>
          <el-button type="primary" @click="openAddDialog" v-if="!isStudent">
            <el-icon><Plus /></el-icon> 布置作业
          </el-button>
        </div>
      </template>

      <div class="filter-row">
        <el-radio-group v-model="archiveFilter" @change="fetchHomeworks">
          <el-radio-button :value="false">未归档</el-radio-button>
          <el-radio-button :value="true">已归档</el-radio-button>
          <el-radio-button :value="null">全部</el-radio-button>
        </el-radio-group>
        <el-select v-model="filterClassId" placeholder="选择班级" clearable style="width: 150px;" @change="fetchHomeworks">
          <el-option v-for="cls in classes" :key="cls.id" :label="cls.name" :value="cls.id" />
        </el-select>
        <el-select v-model="filterSubjectId" placeholder="选择科目" clearable style="width: 140px;" @change="fetchHomeworks">
          <el-option v-for="sub in subjects" :key="sub.id" :label="sub.name" :value="sub.id" />
        </el-select>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table :data="homeworks" v-loading="loading" stripe :row-class-name="rowClassName">
        <el-table-column prop="title" label="作业标题" min-width="150" show-overflow-tooltip />
        <el-table-column prop="class_name" label="班级" width="110" />
        <el-table-column prop="subject_name" label="科目" width="90">
          <template #default="{ row }">{{ row.subject_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusMeta(row.due_status).type" size="small" :effect="row.due_status === 'due_soon' ? 'dark' : 'light'">
              {{ statusMeta(row.due_status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="due_date" label="截止日期" width="170">
          <template #default="{ row }">
            <div>{{ formatDate(row.due_date) }}</div>
            <div v-if="remainingText(row)" class="remaining" :class="row.due_status">{{ remainingText(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="发布人" width="90" />
        <el-table-column prop="created_at" label="发布时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" v-if="!isStudent">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="viewHomework(row)">查看</el-button>
            <el-button v-if="!row.is_archived" size="small" type="success" plain @click="toggleArchive(row, true)">归档</el-button>
            <el-button v-else size="small" type="info" plain @click="toggleArchive(row, false)">取消归档</el-button>
            <el-button size="small" type="danger" @click="deleteHomework(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > 0"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchHomeworks"
        @current-change="fetchHomeworks"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="作业标题" required>
          <el-input v-model="form.title" placeholder="请输入作业标题" />
        </el-form-item>
        <el-form-item label="所属班级" required>
          <el-select v-model="form.class_id" placeholder="请选择班级">
            <el-option v-for="cls in classes" :key="cls.id" :label="cls.name" :value="cls.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属科目">
          <el-select v-model="form.subject_id" placeholder="请选择科目" clearable>
            <el-option v-for="sub in subjects" :key="sub.id" :label="sub.name" :value="sub.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="form.due_date" type="datetime" placeholder="选择截止日期" />
        </el-form-item>
        <el-form-item label="作业内容">
          <el-input v-model="form.content" type="textarea" :rows="6" placeholder="请输入作业内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">{{ dialogMode === 'add' ? '发布' : '保存' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="作业详情" width="600px">
      <el-descriptions :column="2" border v-if="currentHomework">
        <el-descriptions-item label="作业标题">{{ currentHomework.title }}</el-descriptions-item>
        <el-descriptions-item label="所属班级">{{ currentHomework.class_name }}</el-descriptions-item>
        <el-descriptions-item label="所属科目">{{ currentHomework.subject_name || '无' }}</el-descriptions-item>
        <el-descriptions-item label="截止日期">{{ formatDate(currentHomework.due_date) }}</el-descriptions-item>
        <el-descriptions-item label="发布人">{{ currentHomework.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="发布时间">{{ formatDate(currentHomework.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="作业内容" :span="2">{{ currentHomework.content || '无' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Plus } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

const userStore = useUserStore()
const isStudent = computed(() => userStore.userInfo?.role === 'student')

const homeworks = ref([])
const classes = ref([])
const subjects = ref([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filterClassId = ref(null)
const filterSubjectId = ref(null)
// 默认只看未归档（进行中的作业）；true=已归档；null=全部
const archiveFilter = ref(false)

const dialogVisible = ref(false)
const dialogMode = ref('add')
const dialogTitle = computed(() => dialogMode.value === 'add' ? '布置作业' : '编辑作业')

const detailVisible = ref(false)
const currentHomework = ref(null)

const form = ref({
  title: '',
  content: '',
  class_id: null,
  subject_id: null,
  due_date: null
})

const STATUS_META = {
  archived: { label: '已归档', type: 'info' },
  overdue: { label: '已截止', type: 'danger' },
  due_soon: { label: '即将截止', type: 'warning' },
  ongoing: { label: '进行中', type: 'success' },
  no_due: { label: '未设截止', type: '' }
}

const statusMeta = (status) => STATUS_META[status] || { label: '—', type: 'info' }

// 截止剩余时间副文本（即将截止/进行中显示）
const remainingText = (row) => {
  if (row.is_archived || !row.due_date) return ''
  const ms = new Date(row.due_date) - new Date()
  if (ms < 0) return '已超时'
  const hours = Math.floor(ms / 3600000)
  if (hours < 24) return `剩 ${hours} 小时`
  const days = Math.floor(hours / 24)
  return `剩 ${days} 天`
}

const rowClassName = ({ row }) => (row.is_archived ? 'archived-row' : '')

const fetchClasses = async () => {
  try {
    const res = await api.get('/classes')
    classes.value = res.data
  } catch (e) {
    console.error('获取班级失败', e)
  }
}

const fetchSubjects = async () => {
  try {
    const res = await api.get('/subjects')
    subjects.value = res.data
  } catch (e) {
    console.error('获取科目失败', e)
  }
}

const fetchHomeworks = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value
    }
    if (filterClassId.value) params.class_id = filterClassId.value
    if (filterSubjectId.value) params.subject_id = filterSubjectId.value
    if (archiveFilter.value !== null) params.archived = archiveFilter.value

    const res = await api.get('/homeworks', { params })
    homeworks.value = res.data.data
    total.value = res.data.total
  } catch (e) {
    ElMessage.error('获取作业列表失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filterClassId.value = null
  filterSubjectId.value = null
  archiveFilter.value = false
  fetchHomeworks()
}

const openAddDialog = () => {
  dialogMode.value = 'add'
  form.value = {
    title: '',
    content: '',
    class_id: null,
    subject_id: null,
    due_date: null
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.value.title || !form.value.class_id) {
    ElMessage.warning('请填写标题和选择班级')
    return
  }

  submitting.value = true
  try {
    const data = {
      ...form.value,
      due_date: form.value.due_date ? new Date(form.value.due_date).toISOString() : null
    }

    if (dialogMode.value === 'add') {
      await api.post('/homeworks', data)
      ElMessage.success('作业发布成功')
    }

    dialogVisible.value = false
    fetchHomeworks()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || '未知错误'))
  } finally {
    submitting.value = false
  }
}

const viewHomework = async (row) => {
  try {
    const res = await api.get(`/homeworks/${row.id}`)
    currentHomework.value = res.data
    detailVisible.value = true
  } catch (e) {
    ElMessage.error('获取作业详情失败')
  }
}

const toggleArchive = async (row, archived) => {
  try {
    if (archived) {
      await ElMessageBox.confirm(`确定归档「${row.title}」吗？归档表示已检查完成，默认列表将不再显示。`, '归档作业', { type: 'info' })
    }
    await api.put(`/homeworks/${row.id}/archive`, { is_archived: archived })
    ElMessage.success(archived ? '已归档' : '已取消归档')
    fetchHomeworks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败：' + (e.response?.data?.detail || '未知错误'))
    }
  }
}

const deleteHomework = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个作业吗？', '提示', { type: 'warning' })
    await api.delete(`/homeworks/${row.id}`)
    ElMessage.success('删除成功')
    fetchHomeworks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const formatDate = (date) => {
  if (!date) return '无'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchClasses()
  fetchSubjects()
  fetchHomeworks()
})
</script>

<style scoped>
.homework-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: bold; }
.filter-row { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }

.remaining { font-size: 12px; color: #909399; margin-top: 2px; }
.remaining.due_soon { color: #e6a23c; font-weight: bold; }
.remaining.ongoing { color: #67c23a; }

:deep(.archived-row) { color: #c0c4cc; }
:deep(.archived-row .el-tag) { opacity: 0.6; }
</style>
