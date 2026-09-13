<template>
  <div class="rankings">
    <div class="page-header">
      <h1 class="page-title">班级排名</h1>
    </div>

    <!-- 科目排名 -->
    <div class="chart-card">
      <div class="card-toolbar">
        <h3 class="card-title">科目排名</h3>
        <div>
          <el-select v-model="selectedSubject" placeholder="选择科目" style="width: 160px; margin-right: 10px;" @change="loadSubjectRankings">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <el-select v-model="semester" placeholder="选择学期" clearable style="width: 150px; margin-right: 10px;" @change="loadSubjectRankings">
            <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
          </el-select>
          <el-select v-model="examType" placeholder="考试类型" clearable style="width: 140px;" @change="loadSubjectRankings">
            <el-option v-for="t in examTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </div>
      </div>
      <el-table :data="subjectRankings" style="width: 100%" max-height="360" v-loading="rankingLoading">
        <el-table-column prop="rank" label="排名" width="80">
          <template #default="{ row }">
            <el-tag :type="getRankType(row.rank)">{{ row.rank }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="学生" />
        <el-table-column prop="score" label="成绩" />
        <el-table-column prop="exam_type" label="考试类型" />
        <el-table-column prop="semester" label="学期" />
        <template #empty>
          <el-empty description="暂无该科目的成绩数据" />
        </template>
      </el-table>
    </div>

    <!-- 学生单科成绩趋势 -->
    <div class="chart-card" style="margin-top: 20px;">
      <div class="card-toolbar">
        <h3 class="card-title">学生单科成绩趋势</h3>
        <div class="trend-filters">
          <el-select v-model="trendClassId" placeholder="选择班级" style="width: 150px;" @change="handleTrendClassChange">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select v-model="trendSemesters" placeholder="选择学期（可多选）" multiple collapse-tags style="width: 200px;" @change="loadTrend">
            <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
          </el-select>
          <el-select v-model="trendSubjectId" placeholder="选择科目" style="width: 140px;" @change="loadTrend">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <el-select v-model="trendStudentIds" placeholder="选择学生（可多选）" multiple collapse-tags filterable style="width: 220px;" @change="loadTrend">
            <el-option v-for="s in trendStudents" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
      </div>
      <div ref="trendChartRef" style="height: 420px;" v-loading="trendLoading"></div>
      <div v-if="trendEmpty" class="trend-empty-tip">请选择班级、学期、科目和学生后查看成绩变化趋势</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 考试类型：与成绩管理录入/导入的可选考试类型保持一致
const examTypes = [
  { label: '期中考试', value: '期中考试' },
  { label: '期末考试', value: '期末考试' },
  { label: '月考', value: '月考' },
  { label: '测验', value: '测验' },
  { label: '模拟考试', value: '模拟考试' }
]

// ===== 科目排名 =====
const subjects = ref([])
const semesters = ref([])
const selectedSubject = ref(null)
const semester = ref('')
const examType = ref('')
const subjectRankings = ref([])
const rankingLoading = ref(false)

// ===== 学生单科成绩趋势 =====
const classes = ref([])
const trendStudents = ref([])
const trendClassId = ref(null)
const trendSemesters = ref([])
const trendSubjectId = ref(null)
const trendStudentIds = ref([])
const trendLoading = ref(false)
const trendEmpty = ref(true)

const trendChartRef = ref(null)
let trendChart = null

const getRankType = (rank) => {
  if (rank === 1) return 'danger'
  if (rank === 2) return 'warning'
  if (rank === 3) return 'success'
  return 'info'
}

const loadSubjects = async () => {
  const data = await api.subjects.list()
  subjects.value = data || []
  if (subjects.value.length > 0) {
    selectedSubject.value = subjects.value[0].id
    if (!trendSubjectId.value) trendSubjectId.value = subjects.value[0].id
  }
}

const loadSemesters = async () => {
  const data = await api.semesters.list()
  semesters.value = data || []
  // 学期默认为最新学期（学期管理接口按 year/name 倒序，第一个即最新）
  if (semesters.value.length && trendSemesters.value.length === 0) {
    trendSemesters.value = [semesters.value[0].name]
  }
}

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = data || []
  if (classes.value.length) {
    const own = userStore.classId
    trendClassId.value = classes.value.some(c => c.id === own) ? own : classes.value[0].id
  }
}

const loadSubjectRankings = async () => {
  if (!selectedSubject.value) return
  rankingLoading.value = true
  try {
    const data = await api.dashboard.getSubjectRankings(selectedSubject.value, {
      semester: semester.value || undefined,
      exam_type: examType.value || undefined,
      limit: 20
    })
    subjectRankings.value = data || []
  } catch (e) {
    console.error('查询科目排名失败:', e)
  } finally {
    rankingLoading.value = false
  }
}

const loadTrendStudents = async () => {
  trendStudentIds.value = []
  trendStudents.value = []
  if (!trendClassId.value) return
  try {
    const data = await api.students.list({ class_id: trendClassId.value, page: 1, page_size: 1000 })
    trendStudents.value = data?.data || []
  } catch (e) {
    console.error('获取学生失败:', e)
  }
}

const handleTrendClassChange = async () => {
  await loadTrendStudents()
  loadTrend()
}

const loadTrend = async () => {
  const ready = trendClassId.value && trendSemesters.value.length > 0 &&
    trendSubjectId.value && trendStudentIds.value.length > 0
  if (!ready) {
    trendEmpty.value = true
    renderTrendChart({ exams: [], students: [] })
    return
  }
  trendLoading.value = true
  try {
    const data = await api.analytics.getSubjectTrend({
      class_id: trendClassId.value,
      semesters: trendSemesters.value.join(','),
      subject_id: trendSubjectId.value,
      student_ids: trendStudentIds.value.join(',')
    })
    trendEmpty.value = !(data?.students || []).length
    renderTrendChart(data || { exams: [], students: [] })
  } catch (e) {
    console.error('查询单科成绩趋势失败:', e)
  } finally {
    trendLoading.value = false
  }
}

const renderTrendChart = (data) => {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  const exams = data.exams || []
  const students = data.students || []
  const subjectName = subjects.value.find(s => s.id === trendSubjectId.value)?.name || ''

  const series = students.map(stu => ({
    name: stu.student_name,
    type: 'line',
    data: stu.scores,
    smooth: true,
    connectNulls: false,
    symbolSize: 8
  }))

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const lines = [`<b>${params[0]?.axisValue || ''}</b>`]
        params.forEach(p => {
          const v = p.value
          lines.push(`${p.marker} ${p.seriesName}：${v == null ? '无成绩' : v} 分`)
        })
        return lines.join('<br/>')
      }
    },
    legend: { data: students.map(s => s.student_name), bottom: 0 },
    grid: { left: '6%', right: '4%', top: 40, bottom: 60 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: exams.map(e => e.label),
      axisLabel: { rotate: 30 }
    },
    yAxis: {
      type: 'value',
      name: subjectName,
      min: 0,
      max: (value) => Math.max(Math.ceil(value.max), 10)
    },
    series
  }, true)
}

const handleResize = () => trendChart?.resize()

onMounted(async () => {
  await Promise.all([loadClasses(), loadSubjects(), loadSemesters()])
  await loadSubjectRankings()
  await loadTrendStudents()
  await nextTick()
  loadTrend()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
})
</script>

<style scoped>
.rankings {
  padding: 20px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.card-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 15px;
}

.card-title {
  color: #303133;
  font-size: 16px;
  margin: 0;
}

.trend-filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.trend-empty-tip {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 12px 0;
}
</style>
