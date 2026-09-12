<template>
  <div class="subjects">
    <div class="page-header">
      <h1 class="page-title">科目管理</h1>
      <div>
        <el-select v-model="filterClassId" placeholder="选择班级" style="width: 160px; margin-right: 10px;" @change="loadClassSubjects">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" @click="handleAdd" :disabled="!filterClassId">
          <el-icon><Plus /></el-icon>
          新增班级科目
        </el-button>
        <el-button v-if="userStore.isAdmin" @click="handleAddSubject">
          <el-icon><Collection /></el-icon>
          新增标准科目
        </el-button>
      </div>
    </div>

    <div class="table-container">
      <el-table :data="classSubjects" style="width: 100%" v-loading="loading">
        <el-table-column prop="subject_name" label="科目名称" min-width="130" />
        <el-table-column label="任课教师" min-width="120">
          <template #default="{ row }">
            {{ row.teacher_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="电话" min-width="140">
          <template #default="{ row }">
            {{ row.teacher_phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="是否授课" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_teaching ? 'success' : 'info'">{{ row.is_teaching ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否成绩相关" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_score_related ? 'success' : 'info'">{{ row.is_score_related ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="配置时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="filterClassId ? '该班级暂无科目配置，点击「新增班级科目」进行配置' : '请先选择班级'" />
        </template>
      </el-table>
    </div>

    <!-- 新增/编辑班级科目配置 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑班级科目' : '新增班级科目'" width="480px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="班级">
          <el-input :model-value="currentClassName" disabled />
        </el-form-item>
        <el-form-item label="科目" prop="subject_id">
          <el-select v-model="form.subject_id" placeholder="选择标准科目" style="width: 100%;" :disabled="isEdit">
            <el-option v-for="s in availableSubjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否授课" prop="is_teaching">
          <el-radio-group v-model="form.is_teaching">
            <el-radio :value="true">是</el-radio>
            <el-radio :value="false">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="任课教师" prop="teacher_id">
          <el-select v-model="form.teacher_id" placeholder="选择在职教师" style="width: 100%;" clearable filterable
            :disabled="!form.is_teaching">
            <el-option v-for="t in activeTeachers" :key="t.id" :label="`${t.teacher_name}${t.course ? '（' + t.course + '）' : ''}`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否成绩相关" prop="is_score_related">
          <el-radio-group v-model="form.is_score_related">
            <el-radio :value="true">是</el-radio>
            <el-radio :value="false">否</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增标准科目（仅管理员） -->
    <el-dialog v-model="subjectDialogVisible" title="新增标准科目" width="400px">
      <el-form :model="subjectForm" :rules="subjectRules" ref="subjectFormRef" label-width="90px">
        <el-form-item label="科目名称" prop="name">
          <el-input v-model="subjectForm.name" placeholder="如: 数学" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subjectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="subjectSaving" @click="handleSubjectSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Collection } from '@element-plus/icons-vue'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const classes = ref([])
const subjects = ref([])
const teachers = ref([])
const classSubjects = ref([])
const loading = ref(false)

const filterClassId = ref(null)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref(null)

const subjectDialogVisible = ref(false)
const subjectSaving = ref(false)
const subjectFormRef = ref(null)

const form = reactive({
  subject_id: null,
  teacher_id: null,
  is_teaching: true,
  is_score_related: true
})

const subjectForm = reactive({
  name: ''
})

const rules = {
  subject_id: [{ required: true, message: '请选择标准科目', trigger: 'change' }]
}

const subjectRules = {
  name: [{ required: true, message: '请输入科目名称', trigger: 'blur' }]
}

const currentClassName = computed(() =>
  classes.value.find(c => c.id === (isEdit.value ? editingClassId.value : filterClassId.value))?.name || '-'
)
const editingClassId = ref(null)

// 在职教师（科目配置仅允许选择在职教师）
const activeTeachers = computed(() => teachers.value.filter(t => t.employment_status === '在职'))

// 可配置科目 = 底表全部科目 - 该班级已配置科目
const availableSubjects = computed(() => {
  const configured = new Set(classSubjects.value.map(cs => cs.subject_id))
  return subjects.value.filter(s => !configured.has(s.id))
})

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = data || []
  if (classes.value.length) {
    const own = userStore.classId
    filterClassId.value = classes.value.some(c => c.id === own) ? own : classes.value[0].id
  }
}

const loadSubjects = async () => {
  subjects.value = (await api.subjects.list()) || []
}

const loadTeachers = async () => {
  teachers.value = (await api.teachers.list()) || []
}

const loadClassSubjects = async () => {
  if (!filterClassId.value) {
    classSubjects.value = []
    return
  }
  loading.value = true
  try {
    classSubjects.value = (await api.subjects.getClassSubjects(filterClassId.value)) || []
  } catch (e) {
    console.error('查询班级科目配置失败:', e)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, { subject_id: null, teacher_id: null, is_teaching: true, is_score_related: true })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingId.value = row.id
  editingClassId.value = row.class_id
  Object.assign(form, {
    subject_id: row.subject_id,
    teacher_id: row.teacher_id,
    is_teaching: row.is_teaching,
    is_score_related: row.is_score_related
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除「${currentClassName.value} - ${row.subject_name}」的科目配置吗？已有成绩数据时删除将被拒绝。`,
      '删除班级科目',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await api.subjects.deleteClassSubject(row.id)
    ElMessage.success('删除成功')
    loadClassSubjects()
  } catch (e) {
    console.error('删除班级科目配置失败:', e)
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  if (!form.is_teaching && form.teacher_id != null) {
    ElMessage.warning('不授课时不能选择任课教师')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await api.subjects.updateClassSubject(editingId.value, {
        teacher_id: form.teacher_id,
        is_teaching: form.is_teaching,
        is_score_related: form.is_score_related
      })
      ElMessage.success('修改成功')
    } else {
      await api.subjects.createClassSubject({
        class_id: filterClassId.value,
        subject_id: form.subject_id,
        teacher_id: form.teacher_id,
        is_teaching: form.is_teaching,
        is_score_related: form.is_score_related
      })
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadClassSubjects()
  } catch (e) {
    console.error('保存班级科目配置失败:', e)
  } finally {
    saving.value = false
  }
}

const handleAddSubject = () => {
  subjectForm.name = ''
  subjectDialogVisible.value = true
}

const handleSubjectSubmit = async () => {
  await subjectFormRef.value.validate()
  subjectSaving.value = true
  try {
    await api.subjects.create({ name: subjectForm.name })
    ElMessage.success('标准科目新增成功')
    subjectDialogVisible.value = false
    await loadSubjects()
  } catch (e) {
    console.error('新增标准科目失败:', e)
  } finally {
    subjectSaving.value = false
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(async () => {
  await loadClasses()
  await Promise.all([loadSubjects(), loadTeachers()])
  await loadClassSubjects()
})
</script>

<style scoped>
.subjects {
  padding: 20px;
}
</style>
