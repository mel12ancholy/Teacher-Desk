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

    <!-- 新增/编辑标准科目（仅管理员） -->
    <el-dialog v-model="subjectDialogVisible" :title="isEditSubject ? '编辑标准科目' : '新增标准科目'" width="400px">
      <el-alert v-if="isEditSubject" type="info" :closable="false" style="margin-bottom: 12px;"
        title="成绩和班级科目配置通过科目ID关联，改名后所有引用处自动显示新名称" />
      <el-form :model="subjectForm" :rules="subjectRules" ref="subjectFormRef" label-width="90px">
        <el-form-item label="科目名称" prop="name">
          <el-input v-model="subjectForm.name" placeholder="如: 数学" />
        </el-form-item>
        <el-form-item label="默认满分" prop="full_score">
          <el-input-number v-model="subjectForm.full_score" :min="1" :max="300" :step="10" />
          <span class="standard-tip" style="margin-left: 8px;">成绩录入/导入的上限，及格线按满分 60% 折算</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subjectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="subjectSaving" @click="handleSubjectSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 标准科目管理（仅管理员） -->
    <div class="standard-card" v-if="userStore.isAdmin">
      <div class="standard-header">
        <h3 class="standard-title">标准科目管理（{{ subjects.length }}）</h3>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="standard-tip">默认满分用于成绩校验与得分率折算，可被考试类型/场次级配置覆盖</span>
          <el-button type="warning" size="small" @click="openExamTypeDialog">考试类型满分</el-button>
        </div>
      </div>
      <el-table :data="subjects" style="width: 100%" size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="科目名称" min-width="140" />
        <el-table-column label="默认满分" width="100" align="center">
          <template #default="{ row }">
            <span class="full-score">{{ row.full_score ?? 100 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEditSubject(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDeleteSubject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 考试类型满分配置（科目 × 考试类型） -->
    <el-dialog v-model="examTypeDialogVisible" title="考试类型满分配置" width="640px">
      <el-alert type="info" :closable="false" style="margin-bottom: 12px;"
        title="为「科目 × 考试类型」设置默认满分（如：数学×模拟考试=150）。导入成绩时按 科目默认 → 考试类型默认 → 场次实例 的顺序生效。" />
      <el-form :inline="true" style="margin-bottom: 8px;">
        <el-form-item label="科目">
          <el-select v-model="examTypeForm.subject_id" placeholder="选择科目" style="width: 140px;">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="考试类型">
          <el-select v-model="examTypeForm.exam_type" placeholder="选择或输入" filterable allow-create style="width: 140px;">
            <el-option v-for="t in commonExamTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="满分">
          <el-input-number v-model="examTypeForm.full_score" :min="1" :max="300" style="width: 120px;" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleUpsertExamTypeFullScore">保存</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="examTypeFullScores" size="small" border stripe max-height="320">
        <el-table-column prop="subject_name" label="科目" width="110" />
        <el-table-column prop="exam_type" label="考试类型" width="120" />
        <el-table-column prop="full_score" label="满分" width="80" align="center" />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="handleDeleteExamTypeFullScore(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无考试类型满分配置，全部按科目默认满分" :image-size="50" />
        </template>
      </el-table>
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
const isEditSubject = ref(false)
const editingSubjectRowId = ref(null)

const form = reactive({
  subject_id: null,
  teacher_id: null,
  is_teaching: true,
  is_score_related: true
})

const subjectForm = reactive({
  name: '',
  full_score: 100
})

// 考试类型满分配置
const examTypeDialogVisible = ref(false)
const examTypeFullScores = ref([])
const commonExamTypes = ['期中考试', '期末考试', '月考', '测验', '模拟考试']
const examTypeForm = reactive({ subject_id: null, exam_type: '', full_score: 100 })

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
const editingSubjectId = ref(null)

// 在职教师（科目配置仅允许选择在职教师）
const activeTeachers = computed(() => teachers.value.filter(t => t.employment_status === '在职'))

// 可配置科目 = 底表全部科目 - 该班级已配置科目；编辑模式下需包含当前科目，保证显示科目名称
const availableSubjects = computed(() => {
  const configured = new Set(classSubjects.value.map(cs => cs.subject_id))
  const list = subjects.value.filter(s => !configured.has(s.id))
  if (isEdit.value && editingSubjectId.value != null) {
    const current = subjects.value.find(s => s.id === editingSubjectId.value)
    if (current && !list.some(s => s.id === current.id)) {
      list.unshift(current)
    }
  }
  return list
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
  editingSubjectId.value = row.subject_id
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
  isEditSubject.value = false
  editingSubjectRowId.value = null
  subjectForm.name = ''
  subjectForm.full_score = 100
  subjectDialogVisible.value = true
}

const handleEditSubject = (row) => {
  isEditSubject.value = true
  editingSubjectRowId.value = row.id
  subjectForm.name = row.name
  subjectForm.full_score = row.full_score ?? 100
  subjectDialogVisible.value = true
}

const handleDeleteSubject = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除标准科目「${row.name}」吗？已被成绩数据或班级科目配置引用时删除将被拒绝。`,
      '删除标准科目',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await api.subjects.delete(row.id)
    ElMessage.success('标准科目删除成功')
    await loadSubjects()
    await loadClassSubjects()
  } catch (e) {
    console.error('删除标准科目失败:', e)
  }
}

const handleSubjectSubmit = async () => {
  await subjectFormRef.value.validate()
  subjectSaving.value = true
  try {
    if (isEditSubject.value) {
      await api.subjects.update(editingSubjectRowId.value, {
        name: subjectForm.name,
        full_score: subjectForm.full_score
      })
      ElMessage.success('标准科目修改成功，相关成绩与配置将自动显示新名称')
    } else {
      await api.subjects.create({ name: subjectForm.name, full_score: subjectForm.full_score })
      ElMessage.success('标准科目新增成功')
    }
    subjectDialogVisible.value = false
    await loadSubjects()
    await loadClassSubjects()
  } catch (e) {
    console.error('保存标准科目失败:', e)
  } finally {
    subjectSaving.value = false
  }
}

// ===== 考试类型满分 =====
const loadExamTypeFullScores = async () => {
  try {
    examTypeFullScores.value = (await api.subjects.listExamTypeFullScores()) || []
  } catch (e) {
    console.error('查询考试类型满分失败', e)
  }
}

const openExamTypeDialog = () => {
  examTypeForm.subject_id = subjects.value[0]?.id || null
  examTypeForm.exam_type = ''
  examTypeForm.full_score = 100
  loadExamTypeFullScores()
  examTypeDialogVisible.value = true
}

const handleUpsertExamTypeFullScore = async () => {
  if (!examTypeForm.subject_id || !examTypeForm.exam_type) {
    ElMessage.warning('请选择科目和考试类型')
    return
  }
  try {
    await api.subjects.upsertExamTypeFullScore({ ...examTypeForm })
    ElMessage.success('已保存')
    loadExamTypeFullScores()
  } catch (e) {
    console.error('保存考试类型满分失败', e)
  }
}

const handleDeleteExamTypeFullScore = async (row) => {
  try {
    await api.subjects.deleteExamTypeFullScore(row.id)
    ElMessage.success('已删除，该组合回落到科目默认满分')
    loadExamTypeFullScores()
  } catch (e) {
    console.error('删除考试类型满分失败', e)
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

.standard-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-top: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.standard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.standard-title {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.standard-tip {
  font-size: 12px;
  color: #909399;
}
</style>
