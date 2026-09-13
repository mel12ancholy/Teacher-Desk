<template>
  <div class="teachers">
    <div class="page-header">
      <h1 class="page-title">任课教师管理</h1>
      <el-button type="primary" @click="handleAdd" v-if="userStore.isAdmin">
        <el-icon><Plus /></el-icon>
        新增教师
      </el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <el-select v-model="filterStatus" placeholder="在职状态" clearable style="width: 130px; margin-right: 10px;" @change="loadTeachers">
          <el-option label="在职" value="在职" />
          <el-option label="离职" value="离职" />
        </el-select>
        <el-input v-model="filterKeyword" placeholder="搜索姓名/课程" clearable style="width: 200px" @clear="loadTeachers" @keyup.enter="loadTeachers" />
        <el-button type="primary" @click="loadTeachers">查询</el-button>
      </div>
    </el-card>

    <div class="table-container">
      <el-table :data="teachers" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="teacher_name" label="教师姓名" min-width="120" />
        <el-table-column prop="course" label="授课课程" min-width="120">
          <template #default="{ row }">
            {{ row.course || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="电话" min-width="140">
          <template #default="{ row }">
            {{ row.phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="employment_status" label="在职状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.employment_status === '在职' ? 'success' : 'info'">{{ row.employment_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" v-if="userStore.isAdmin">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button
              :type="row.employment_status === '在职' ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(row)"
            >
              {{ row.employment_status === '在职' ? '设为离职' : '恢复在职' }}
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑教师' : '新增教师'" width="460px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="教师姓名" prop="teacher_name">
          <el-input v-model="form.teacher_name" placeholder="请输入教师姓名" />
        </el-form-item>
        <el-form-item label="授课课程" prop="course">
          <el-select v-model="form.course" placeholder="选择标准科目（与科目管理联动）" style="width: 100%;" clearable filterable>
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入联系电话" />
        </el-form-item>
        <el-form-item label="在职状态" prop="employment_status">
          <el-select v-model="form.employment_status" style="width: 100%">
            <el-option label="在职" value="在职" />
            <el-option label="离职" value="离职" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const teachers = ref([])
const subjects = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)

const filterStatus = ref('')
const filterKeyword = ref('')

const form = reactive({
  teacher_name: '',
  course: '',
  phone: '',
  employment_status: '在职'
})

const rules = {
  teacher_name: [{ required: true, message: '请输入教师姓名', trigger: 'blur' }],
  employment_status: [{ required: true, message: '请选择在职状态', trigger: 'change' }]
}

const loadTeachers = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.employment_status = filterStatus.value
    if (filterKeyword.value) params.keyword = filterKeyword.value
    teachers.value = (await api.teachers.list(params)) || []
  } catch (e) {
    console.error('查询教师失败:', e)
  } finally {
    loading.value = false
  }
}

const loadSubjects = async () => {
  try {
    subjects.value = (await api.subjects.list()) || []
  } catch (e) {
    console.error('获取标准科目失败:', e)
  }
}

const handleAdd = () => {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, { teacher_name: '', course: '', phone: '', employment_status: '在职' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    teacher_name: row.teacher_name,
    course: row.course || '',
    phone: row.phone || '',
    employment_status: row.employment_status
  })
  dialogVisible.value = true
}

const handleToggleStatus = async (row) => {
  const target = row.employment_status === '在职' ? '离职' : '在职'
  const tip = target === '离职'
    ? `确认将「${row.teacher_name}」设为离职吗？离职后科目管理中将不能选择该教师。`
    : `确认恢复「${row.teacher_name}」为在职吗？`
  try {
    await ElMessageBox.confirm(tip, '在职状态', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  try {
    await api.teachers.update(row.id, { employment_status: target })
    ElMessage.success('状态已更新')
    loadTeachers()
  } catch (e) {
    console.error('更新在职状态失败:', e)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除教师「${row.teacher_name}」吗？若已被班级科目配置引用，删除将被拒绝。`,
      '删除教师',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await api.teachers.delete(row.id)
    ElMessage.success('删除成功')
    loadTeachers()
  } catch (e) {
    console.error('删除教师失败:', e)
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  saving.value = true
  try {
    if (isEdit.value) {
      await api.teachers.update(editingId.value, { ...form })
      ElMessage.success('修改成功')
    } else {
      await api.teachers.create({ ...form })
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadTeachers()
  } catch (e) {
    console.error('保存教师失败:', e)
  } finally {
    saving.value = false
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadTeachers()
  loadSubjects()
})
</script>

<style scoped>
.teachers {
  padding: 20px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
