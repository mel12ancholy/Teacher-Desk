<template>
  <div class="students">
    <div class="page-header">
      <h1 class="page-title">学生管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>
          新增学生
        </el-button>
        <el-button type="success" @click="showBatchDialog = true">
          <el-icon><Upload /></el-icon>
          批量导入
        </el-button>
        <el-button type="warning" @click="showBatchEditDialog = true" :disabled="selectedStudents.length === 0">
          <el-icon><Edit /></el-icon>
          批量修改 ({{ selectedStudents.length }})
        </el-button>
        <el-button type="danger" @click="handleBatchDelete" :disabled="selectedStudents.length === 0">
          <el-icon><Delete /></el-icon>
          批量删除 ({{ selectedStudents.length }})
        </el-button>
        <el-button type="info" @click="handleExportStudents" :loading="exportLoading">
          <el-icon><Download /></el-icon>
          导出学生
        </el-button>
      </div>
    </div>

    <el-card class="filter-card" shadow="never">
      <el-form :model="filterForm" inline>
        <el-form-item label="筛选条件">
          <el-collapse-transition>
            <div v-show="showAdvancedFilter" class="advanced-filter">
              <el-form-item label="班级">
                <el-select v-model="filterForm.class_id" placeholder="全部班级" clearable style="width: 180px;">
                  <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
              </el-form-item>

              <el-form-item label="姓名">
                <el-input v-model="filterForm.name" placeholder="输入姓名" clearable style="width: 150px;" />
              </el-form-item>

              <el-form-item label="学号">
                <el-input v-model="filterForm.student_no" placeholder="输入学号" clearable style="width: 150px;" />
              </el-form-item>

              <el-form-item label="性别">
                <el-select v-model="filterForm.gender" placeholder="全部" clearable style="width: 100px;">
                  <el-option label="男" value="male" />
                  <el-option label="女" value="female" />
                </el-select>
              </el-form-item>

              <el-form-item label="电话">
                <el-input v-model="filterForm.phone" placeholder="输入电话" clearable style="width: 150px;" />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="applyFilter">筛选</el-button>
                <el-button @click="resetFilter">重置</el-button>
                <el-button type="info" @click="saveSearchCondition" :disabled="!hasFilterCondition">
                  <el-icon><Star /></el-icon> 保存条件
                </el-button>
              </el-form-item>
            </div>
          </el-collapse-transition>
        </el-form-item>

        <el-form-item>
          <el-button @click="showAdvancedFilter = !showAdvancedFilter" type="default">
            {{ showAdvancedFilter ? '收起筛选' : '展开高级筛选' }}
            <el-icon>
              <ArrowUp v-if="showAdvancedFilter" />
              <ArrowDown v-else />
            </el-icon>
          </el-button>

          <el-tag v-if="activeFilterCount > 0" type="primary" style="margin-left: 10px;">
            已设置 {{ activeFilterCount }} 个筛选条件
          </el-tag>
        </el-form-item>
      </el-form>

      <div v-if="savedSearches.length > 0" class="saved-searches">
        <el-divider content-position="left">
          <el-icon><Collection /></el-icon> 已保存的搜索条件
        </el-divider>
        <el-tag
          v-for="(search, index) in savedSearches"
          :key="index"
          class="saved-search-tag"
          closable
          @close="removeSearchCondition(index)"
          @click="loadSearchCondition(search)"
          type="info"
        >
          {{ search.name || `条件 ${index + 1}` }}
        </el-tag>
      </div>
    </el-card>

    <div class="table-container">
      <el-table :data="students" style="width: 100%" v-loading="loading" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="student_no" label="学号" />
        <el-table-column prop="gender" label="性别" width="80">
          <template #default="{ row }">
            {{ row.gender === 'male' ? '男' : row.gender === 'female' ? '女' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" />
        <el-table-column prop="phone" label="电话" />
        <el-table-column prop="parent_phone" label="家长电话" />
        <el-table-column label="家长码" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.parent_code" type="success" @click="copyParentCode(row.parent_code)" style="cursor: pointer;">
              {{ row.parent_code }}
            </el-tag>
            <el-tag v-else type="info">未生成</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="!row.parent_code" type="success" size="small" @click="generateParentCode(row)" :loading="row.generating">
              生成家长码
            </el-button>
            <el-button v-else type="warning" size="small" @click="resetParentCode(row)" :loading="row.generating">
              重置
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadStudents"
        @current-change="loadStudents"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </div>

    <!-- 新增/编辑学生 -->
    <StudentFormDialog
      v-model="dialogVisible"
      :is-edit="isEdit"
      :student="editingStudent"
      :classes="classes"
      @submit="handleSubmit"
    />

    <!-- 批量导入 -->
    <StudentBatchImportDialog
      v-model="showBatchDialog"
      :classes="classes"
      @imported="handleImported"
    />

    <!-- 导入结果 -->
    <ImportResultDialog v-model="showResultDialog" :result="importResult" />

    <!-- 批量修改 -->
    <StudentBatchEditDialog
      v-model="showBatchEditDialog"
      :classes="classes"
      :selected-students="selectedStudents"
      @done="handleBatchEditDone"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Collection, ArrowUp, ArrowDown, Star, Edit, Delete } from '@element-plus/icons-vue'
import axios from 'axios'
import api from '@/api'
import * as XLSX from 'xlsx'
import StudentFormDialog from '@/components/students/StudentFormDialog.vue'
import StudentBatchImportDialog from '@/components/students/StudentBatchImportDialog.vue'
import ImportResultDialog from '@/components/students/ImportResultDialog.vue'
import StudentBatchEditDialog from '@/components/students/StudentBatchEditDialog.vue'

const baseURL = '/api'

const students = ref([])
const classes = ref([])
const loading = ref(false)
const selectedStudents = ref([])
const exportLoading = ref(false)

// 弹窗状态
const dialogVisible = ref(false)
const showBatchDialog = ref(false)
const showResultDialog = ref(false)
const showBatchEditDialog = ref(false)
const isEdit = ref(false)
const editingStudent = ref(null)
const importResult = ref(null)

// 列表查询
const searchName = ref('')
const filterClassId = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 高级筛选
const showAdvancedFilter = ref(false)
const filterForm = reactive({
  class_id: null,
  name: '',
  student_no: '',
  gender: '',
  phone: ''
})
const savedSearches = ref([])

const getAuthHeader = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadClasses = async () => {
  const res = await axios.get(`${baseURL}/classes`, { headers: getAuthHeader() })
  classes.value = (res.data || []).filter(c => c.id)
}

const loadStudents = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${baseURL}/students`, {
      params: {
        class_id: filterClassId.value,
        name: searchName.value,
        page: page.value,
        page_size: pageSize.value
      },
      headers: getAuthHeader()
    })
    students.value = res.data?.data || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  editingStudent.value = null
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingStudent.value = row
  dialogVisible.value = true
}

const handleSubmit = async (formData) => {
  try {
    if (isEdit.value) {
      await axios.put(`${baseURL}/students/${editingStudent.value.id}`, formData, { headers: getAuthHeader() })
      ElMessage.success('修改成功')
    } else {
      await axios.post(`${baseURL}/students`, formData, { headers: getAuthHeader() })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadStudents()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const copyParentCode = (code) => {
  navigator.clipboard.writeText(code)
  ElMessage.success(`家长码 ${code} 已复制到剪贴板`)
}

const generateParentCode = async (row) => {
  try {
    row.generating = true
    const res = await axios.post(`${baseURL}/parent/students/${row.id}/generate-code`, {}, { headers: getAuthHeader() })
    row.parent_code = res.data.parent_code
    ElMessage.success(`家长码已生成：${res.data.parent_code}`)
    loadStudents()
  } catch (e) {
    ElMessage.error('生成家长码失败：' + (e.response?.data?.detail || '未知错误'))
  } finally {
    row.generating = false
  }
}

const resetParentCode = async (row) => {
  try {
    await ElMessageBox.confirm('确定要重置家长码吗？重置后旧码将失效！', '提示', { type: 'warning' })
    row.generating = true
    const res = await axios.post(`${baseURL}/parent/students/${row.id}/generate-code`, {}, { headers: getAuthHeader() })
    row.parent_code = res.data.parent_code
    ElMessage.success(`家长码已重置为：${res.data.parent_code}`)
    loadStudents()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('重置家长码失败：' + (e.response?.data?.detail || '未知错误'))
    }
  } finally {
    row.generating = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定删除该学生吗？将同时清除其成绩、考勤、超行分、座位与积分数据，操作不可恢复！',
      '提示',
      { type: 'warning' }
    )
  } catch {
    // 用户取消或关闭确认框，不算错误
    return
  }
  try {
    await axios.delete(`${baseURL}/students/${row.id}`, { headers: getAuthHeader() })
    ElMessage.success('删除成功')
    loadStudents()
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message || '未知错误'))
  }
}

const handleSelectionChange = (selection) => {
  selectedStudents.value = selection
}

const handleBatchDelete = async () => {
  if (selectedStudents.value.length === 0) {
    ElMessage.warning('请先选择要删除的学生')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedStudents.value.length} 名学生吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    loading.value = true
    let successCount = 0
    let failCount = 0
    let errorMessages = []

    for (const student of selectedStudents.value) {
      try {
        await api.students.delete(student.id)
        successCount++
      } catch (e) {
        failCount++
        const errorMsg = e.response?.data?.detail || e.message || '未知错误'
        errorMessages.push(`${student.name}: ${errorMsg}`)
        console.error(`删除学生 ${student.name} 失败:`, errorMsg, e)
      }
    }

    loading.value = false
    selectedStudents.value = []
    loadStudents()

    if (failCount === 0) {
      ElMessage.success(`成功删除 ${successCount} 名学生`)
    } else {
      ElMessage.error({
        message: `成功删除 ${successCount} 名学生，${failCount} 名删除失败\n失败原因：${errorMessages.join('; ')}`,
        duration: 5000
      })
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      console.error('批量删除异常:', e)
      ElMessage.error('批量删除失败')
    }
  }
}

const handleImported = (result) => {
  importResult.value = result
  showResultDialog.value = true
  loadStudents()
}

const handleBatchEditDone = ({ successCount, failCount, errorMessages }) => {
  showBatchEditDialog.value = false
  selectedStudents.value = []
  loadStudents()

  if (failCount === 0) {
    ElMessage.success(`成功修改 ${successCount} 名学生`)
  } else {
    ElMessage.error({
      message: `成功修改 ${successCount} 名学生，${failCount} 名修改失败\n失败原因：${errorMessages.join('; ')}`,
      duration: 5000
    })
  }
}

const handleExportStudents = async () => {
  try {
    exportLoading.value = true

    const data = await api.students.list({
      class_id: filterClassId.value || undefined,
      page: 1,
      page_size: 1000
    })

    const studentsList = data?.data || []

    if (studentsList.length === 0) {
      ElMessage.warning('没有学生数据可导出')
      exportLoading.value = false
      return
    }

    const exportData = [
      ['姓名', '学号', '性别', '班级', '电话', '家长电话', '地址']
    ]

    studentsList.forEach(s => {
      exportData.push([
        s.name || '',
        s.student_no || '',
        s.gender === 'male' ? '男' : s.gender === 'female' ? '女' : '',
        s.class_name || '',
        s.phone || '',
        s.parent_phone || '',
        s.address || ''
      ])
    })

    const ws = XLSX.utils.aoa_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '学生名单')

    const timestamp = new Date().toISOString().slice(0, 10)
    XLSX.writeFile(wb, `学生名单_${timestamp}.xlsx`)

    exportLoading.value = false
    ElMessage.success(`成功导出 ${studentsList.length} 名学生`)
  } catch (e) {
    exportLoading.value = false
    console.error('导出学生失败:', e)
    ElMessage.error('导出学生失败')
  }
}

watch([filterClassId], () => {
  page.value = 1
  loadStudents()
})

const activeFilterCount = computed(() => {
  let count = 0
  if (filterForm.class_id) count++
  if (filterForm.name) count++
  if (filterForm.student_no) count++
  if (filterForm.gender) count++
  if (filterForm.phone) count++
  return count
})

const hasFilterCondition = computed(() => {
  return filterForm.class_id ||
         filterForm.name ||
         filterForm.student_no ||
         filterForm.gender ||
         filterForm.phone
})

const applyFilter = () => {
  searchName.value = filterForm.name
  filterClassId.value = filterForm.class_id
  page.value = 1
  loadStudents()
}

const resetFilter = () => {
  filterForm.class_id = null
  filterForm.name = ''
  filterForm.student_no = ''
  filterForm.gender = ''
  filterForm.phone = ''
  searchName.value = ''
  filterClassId.value = null
  page.value = 1
  loadStudents()
}

const saveSearchCondition = () => {
  if (!hasFilterCondition.value) {
    ElMessage.warning('请先设置筛选条件')
    return
  }

  ElMessageBox.prompt('请输入保存的名称', '保存筛选条件', {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputValue: `搜索条件 ${savedSearches.value.length + 1}`
  }).then(({ value }) => {
    const searchData = {
      name: value,
      filters: { ...filterForm },
      timestamp: Date.now()
    }

    savedSearches.value.push(searchData)
    localStorage.setItem('studentSearches', JSON.stringify(savedSearches.value))
    ElMessage.success('筛选条件已保存')
  }).catch(() => {})
}

const loadSearchCondition = (search) => {
  Object.assign(filterForm, search.filters)
  searchName.value = filterForm.name
  filterClassId.value = filterForm.class_id
  page.value = 1
  loadStudents()
  ElMessage.success('已加载筛选条件')
}

const removeSearchCondition = (index) => {
  savedSearches.value.splice(index, 1)
  localStorage.setItem('studentSearches', JSON.stringify(savedSearches.value))
  ElMessage.success('已删除保存的筛选条件')
}

onMounted(async () => {
  await loadClasses()

  const saved = localStorage.getItem('studentSearches')
  if (saved) {
    try {
      savedSearches.value = JSON.parse(saved)
    } catch (e) {
      console.error('加载搜索历史失败', e)
    }
  }

  loadStudents()
})
</script>

<style scoped>
.students {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-card {
  margin-bottom: 20px;
}

.advanced-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  padding: 15px 0;
}

.saved-searches {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.saved-search-tag {
  margin-right: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.saved-search-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.table-container {
  background: white;
  padding: 20px;
  border-radius: 4px;
}
</style>
