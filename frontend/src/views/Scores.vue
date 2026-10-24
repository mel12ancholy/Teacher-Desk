<template>
  <div class="scores">
    <div class="page-header">
      <h1 class="page-title">成绩管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd">
          <el-icon><Plus /></el-icon>
          录入成绩
        </el-button>
        <el-button type="success" @click="showBatchDialog = true">
          <el-icon><Upload /></el-icon>
          批量导入
        </el-button>
        <el-divider direction="vertical" />
        <el-button type="info" @click="handleOpenAnalysis">
          <el-icon><DataAnalysis /></el-icon>
          成绩分析
        </el-button>
        <el-button type="warning" @click="showGradeAvgDialog = true">年级均分</el-button>
        <el-button @click="handleExportScores" :loading="exportLoading">
          <el-icon><Download /></el-icon>
          导出成绩
        </el-button>
        <el-divider direction="vertical" />
        <el-button type="danger" plain @click="showBatchDeleteDialog = true">批量删除</el-button>
      </div>
    </div>

    <el-card class="filter-card" shadow="never">
      <div class="filter-bar">
        <span class="filter-label">筛选：</span>
        <el-select v-model="filterClassId" placeholder="选择班级" clearable style="width: 150px;" @change="loadScores">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filterSubjectId" placeholder="选择科目" clearable style="width: 150px;" @change="loadScores">
          <el-option v-for="s in filterSubjectOptions" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-select v-model="filterSemester" placeholder="选择学期" clearable style="width: 120px;" @change="loadScores">
          <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
        </el-select>
        <el-select v-model="filterExamType" placeholder="考试类型" clearable filterable allow-create style="width: 130px;" @change="loadScores">
          <el-option v-for="t in commonExamTypes" :key="t" :label="t" :value="t" />
        </el-select>
      </div>
    </el-card>

    <div class="statistics-card" v-if="statisticsData">
      <el-row :gutter="20">
        <el-col :span="showGradeAvgCard ? 6 : 8">
          <div class="stat-item">
            <div class="stat-label">平均分</div>
            <div class="stat-value">{{ statisticsData.average.toFixed(1) }}</div>
          </div>
        </el-col>
        <el-col :span="showGradeAvgCard ? 6 : 8">
          <div class="stat-item">
            <div class="stat-label">最高分</div>
            <div class="stat-value success">{{ statisticsData.max }}</div>
          </div>
        </el-col>
        <el-col :span="showGradeAvgCard ? 6 : 8">
          <div class="stat-item">
            <div class="stat-label">最低分</div>
            <div class="stat-value danger">{{ statisticsData.min }}</div>
          </div>
        </el-col>
        <el-col :span="6" v-if="showGradeAvgCard">
          <div class="stat-item" :class="{ 'pending': gradeAvgInfo?.value == null }">
            <div class="stat-label">年级平均（{{ gradeAvgInfo?.label || '' }}）</div>
            <div v-if="gradeAvgInfo?.value != null" class="stat-value" style="color: #e6a23c;">{{ gradeAvgInfo.value }}</div>
            <div v-else class="stat-value" style="color: #c0c4cc; font-size: 16px; cursor: pointer;" @click="openGradeAvgEntry">
              待录入（点击录入）
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <div class="table-container">
      <el-table :data="scores" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="student_name" label="学生" />
        <el-table-column prop="subject_name" label="科目" />
        <el-table-column prop="score" label="成绩" width="110">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.score, row.full_score)">
              {{ row.score }}<span v-if="row.full_score && row.full_score !== 100" class="score-full">/{{ row.full_score }}</span>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="exam_type" label="考试类型" width="120" />
        <el-table-column prop="exam_date" label="考试日期" width="120">
          <template #default="{ row }">
            {{ row.exam_date ? formatDate(row.exam_date) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="semester" label="学期" width="100" />
        <el-table-column prop="created_at" label="录入时间" width="180">
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
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadScores"
        @current-change="loadScores"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </div>

    <!-- 录入/编辑成绩 -->
    <ScoreFormDialog
      v-model="dialogVisible"
      :is-edit="isEdit"
      :editing-row="editingRow"
      :students="students"
      :subjects="subjects"
      :semesters="semesters"
      :classes="classes"
      :default-class-id="filterClassId"
      @submit="handleSubmit"
    />

    <!-- 批量导入 -->
    <ScoreBatchImportDialog
      v-model="showBatchDialog"
      :classes="classes"
      :subjects="subjects"
      :semesters="semesters"
      @imported="loadScores"
    />

    <!-- 年级均分录入 -->
    <GradeAverageDialog
      v-model="showGradeAvgDialog"
      :semesters="semesters"
      :score-subjects="scoreSubjectRows"
      :preset-semester="filterSemester"
      :preset-exam-type="filterExamType"
      @saved="loadGradeAvg"
    />

    <!-- 批量删除 -->
    <ScoreBatchDeleteDialog
      v-model="showBatchDeleteDialog"
      :classes="classes"
      :semesters="semesters"
      :subjects="subjects"
      @deleted="loadScores"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, DataAnalysis, Download } from '@element-plus/icons-vue'
import api from '@/api'
import * as XLSX from 'xlsx'
import ScoreFormDialog from '@/components/scores/ScoreFormDialog.vue'
import ScoreBatchImportDialog from '@/components/scores/ScoreBatchImportDialog.vue'
import GradeAverageDialog from '@/components/scores/GradeAverageDialog.vue'
import ScoreBatchDeleteDialog from '@/components/scores/ScoreBatchDeleteDialog.vue'
import { useClassSubjects } from '@/composables/useClassSubjects'

const router = useRouter()

const scores = ref([])
const classes = ref([])
const subjects = ref([])
const semesters = ref([])
const students = ref([])
const loading = ref(false)
const exportLoading = ref(false)

// 弹窗状态
const dialogVisible = ref(false)
const showBatchDialog = ref(false)
const showGradeAvgDialog = ref(false)
const showBatchDeleteDialog = ref(false)
const isEdit = ref(false)
const editingRow = ref(null)

// 年级平均（选了科目才展示：当前筛选下该科目最近一场考试的录入值）
const gradeAvgInfo = ref(null)
const showGradeAvgCard = computed(() => !!filterSubjectId.value)

// 当前班级的成绩相关科目（年级均分录入表格行；未选班级时回退全部科目）
const scoreSubjectRows = computed(() => {
  if (filterClassId.value) {
    const rows = scoreSubjectsFor(filterClassId.value)
    if (rows.length) return rows
  }
  return subjects.value || []
})

const loadGradeAvg = async () => {
  gradeAvgInfo.value = null
  if (!filterSubjectId.value || !scores.value.length) return
  const rows = scores.value.filter(s => s.subject_id === filterSubjectId.value)
  if (!rows.length) return
  // 定位该科目最近一场考试（优先考试类型筛选内的最新日期）
  const latest = rows.reduce((a, b) => {
    const da = a.exam_date ? String(a.exam_date).slice(0, 10) : ''
    const db = b.exam_date ? String(b.exam_date).slice(0, 10) : ''
    return db >= da ? b : a
  })
  if (!latest.exam_date) return
  try {
    const list = await api.scores.getGradeAverages({
      semester: latest.semester,
      exam_type: latest.exam_type,
      exam_date: String(latest.exam_date).slice(0, 10)
    })
    const hit = (list || []).find(x => x.subject_id === filterSubjectId.value)
    gradeAvgInfo.value = {
      value: hit ? hit.avg_score : null,
      label: `${latest.exam_type}`,
      semester: latest.semester,
      exam_type: latest.exam_type
    }
  } catch (e) {
    console.error('查询年级均分失败', e)
  }
}

const openGradeAvgEntry = () => {
  showGradeAvgDialog.value = true
}

const filterClassId = ref(null)
const filterSubjectId = ref(null)
const filterSemester = ref('')
const filterExamType = ref('')
const commonExamTypes = ['期中考试', '期末考试', '月考', '测验', '模拟考试']
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const statisticsData = ref(null)

const { ensureClassSubjects, scoreSubjectsFor } = useClassSubjects(subjects)

// 顶部筛选科目选项：跟随所选班级
const filterSubjectOptions = computed(() => scoreSubjectsFor(filterClassId.value))

const getScoreType = (score, fullScore = 100) => {
  // 按得分率分档（满分非 100 时折算）
  const pct = score / (fullScore || 100) * 100
  if (pct >= 90) return 'success'
  if (pct >= 60) return 'warning'
  return 'danger'
}

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = (data || []).filter(c => c.id)
}

const loadSubjects = async () => {
  const data = await api.subjects.list()
  subjects.value = data || []
}

const loadSemesters = async () => {
  const data = await api.semesters.list()
  semesters.value = data || []
}

const loadStudents = async () => {
  const data = await api.students.list({ page_size: 1000 })
  students.value = (data?.data || []).filter(s => s.id)
}

const calculateStatistics = () => {
  if (!scores.value || scores.value.length === 0) {
    statisticsData.value = null
    return
  }

  const scores_list = scores.value.map(s => s.score).filter(s => typeof s === 'number')
  if (scores_list.length === 0) {
    statisticsData.value = null
    return
  }

  const average = scores_list.reduce((a, b) => a + b, 0) / scores_list.length
  const max = Math.max(...scores_list)
  const min = Math.min(...scores_list)

  statisticsData.value = { average, max, min }
}

const loadScores = async () => {
  loading.value = true
  try {
    // 班级切换后联动加载该班级科目配置，并清空失效的科目筛选
    if (filterClassId.value) {
      await ensureClassSubjects(filterClassId.value)
      const valid = scoreSubjectsFor(filterClassId.value).some(s => s.id === filterSubjectId.value)
      if (!valid) filterSubjectId.value = null
    }
    const data = await api.scores.list({
      class_id: filterClassId.value,
      subject_id: filterSubjectId.value,
      semester: filterSemester.value,
      exam_type: filterExamType.value || undefined,
      page: page.value,
      page_size: pageSize.value
    })
    scores.value = (data?.data || []).map(s => ({
      ...s,
      student_name: s.student_name || students.value.find(st => st.id === s.student_id)?.name || '',
      subject_name: s.subject_name || subjects.value.find(sub => sub.id === s.subject_id)?.name || ''
    }))
    total.value = data?.total || scores.value.length

    calculateStatistics()
    loadGradeAvg()
  } catch (e) {
    scores.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  editingRow.value = null
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingRow.value = row
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该成绩吗?', '提示', { type: 'warning' })
    await api.scores.delete(row.id)
    ElMessage.success('删除成功')
    loadScores()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async (formData) => {
  try {
    if (isEdit.value) {
      await api.scores.update(editingRow.value.id, {
        subject_id: formData.subject_id,
        score: formData.score,
        exam_type: formData.exam_type,
        exam_date: formData.exam_date,
        semester: formData.semester
      })
      ElMessage.success('修改成功')
    } else {
      await api.scores.create({
        student_id: formData.student_id,
        subject_id: formData.subject_id,
        class_id: students.value.find(s => s.id === formData.student_id)?.class_id || formData.class_id,
        score: formData.score,
        exam_type: formData.exam_type,
        exam_date: formData.exam_date,
        semester: formData.semester
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadScores()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleOpenAnalysis = () => {
  // 携带已选中的筛选条件到成绩分析页（班级/学期/考试类型）
  const query = {}
  if (filterClassId.value) query.class_id = filterClassId.value
  if (filterSemester.value) query.semester = filterSemester.value
  if (filterExamType.value) query.exam_type = filterExamType.value
  if (filterSubjectId.value) query.subject_id = filterSubjectId.value
  router.push({ path: '/analysis', query })
}

const handleExportScores = async () => {
  try {
    exportLoading.value = true

    const data = await api.scores.list({
      class_id: filterClassId.value || undefined,
      subject_id: filterSubjectId.value || undefined,
      semester: filterSemester.value || undefined,
      exam_type: filterExamType.value || undefined,
      page: 1,
      page_size: 1000
    })

    const scoresList = data?.data || []

    if (scoresList.length === 0) {
      ElMessage.warning('没有成绩数据可导出')
      exportLoading.value = false
      return
    }

    const exportData = [
      ['学生姓名', '科目', '成绩', '考试类型', '考试日期', '学期']
    ]

    scoresList.forEach(s => {
      exportData.push([
        s.student_name || '',
        s.subject_name || '',
        s.score || '',
        s.exam_type || '',
        s.exam_date ? s.exam_date.substring(0, 10) : '',
        s.semester || ''
      ])
    })

    const ws = XLSX.utils.aoa_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '成绩单')

    const timestamp = new Date().toISOString().slice(0, 10)
    XLSX.writeFile(wb, `成绩单_${timestamp}.xlsx`)

    exportLoading.value = false
    ElMessage.success(`成功导出 ${scoresList.length} 条成绩记录`)
  } catch (e) {
    exportLoading.value = false
    console.error('导出成绩失败:', e)
    ElMessage.error('导出成绩失败')
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(async () => {
  await Promise.all([loadClasses(), loadSubjects(), loadSemesters(), loadStudents()])
  loadScores()
})
</script>

<style scoped>
.scores {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-label {
  font-size: 14px;
  color: #909399;
}

.statistics-card {
  background: white;
  padding: 20px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
}

.stat-value.success {
  color: #67C23A;
}

.stat-value.danger {
  color: #F56C6C;
}

.table-container {
  background: white;
  padding: 20px;
  border-radius: 4px;
}
</style>
