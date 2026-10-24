<template>
  <div class="dashboard">
    <div class="page-header">
      <h1 class="page-title">数据仪表盘</h1>
      <el-select v-model="semester" placeholder="选择学期" @change="loadAll" style="width: 180px">
        <el-option label="全部" value="" />
        <el-option v-for="s in semesters" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
    </div>

    <!-- 概览统计 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #409eff;">
            <el-icon :size="30"><User /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_students }}</div>
            <div class="stat-label">学生总数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #67c23a;">
            <el-icon :size="30"><School /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_classes }}</div>
            <div class="stat-label">班级数量</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #e6a23c;">
            <el-icon :size="30"><Document /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_scores }}</div>
            <div class="stat-label">成绩记录</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #f56c6c;">
            <el-icon :size="30"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.attendance_rate }}%</div>
            <div class="stat-label">考勤率</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 最近考试报告摘要 + 超行分榜 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <div class="chart-card">
          <div class="card-toolbar">
            <h3>最近考试概况</h3>
            <el-select v-model="examClassId" placeholder="选择班级" size="small" style="width: 140px;" @change="loadLatestExam">
              <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </div>
          <template v-if="examReport">
            <div class="exam-title">
              {{ examReport.exam.label }}
              <el-tag v-if="examReport.prev_exam" type="info" size="small" effect="plain" style="margin-left: 8px;">
                对比 {{ examReport.prev_exam.label }}
              </el-tag>
            </div>
            <el-row :gutter="12" class="exam-metrics">
              <el-col :span="4"><div class="mini-metric"><div class="v">{{ examReport.summary.student_count }}</div><div class="l">参考人数</div></div></el-col>
              <el-col :span="4"><div class="mini-metric"><div class="v blue">{{ examReport.summary.avg }}%</div><div class="l">平均得分率</div></div></el-col>
              <el-col :span="4"><div class="mini-metric"><div class="v green">{{ examReport.summary.pass_rate }}%</div><div class="l">及格率</div></div></el-col>
              <el-col :span="4"><div class="mini-metric"><div class="v orange">{{ examReport.summary.excellent_rate }}%</div><div class="l">优秀率</div></div></el-col>
              <el-col :span="4"><div class="mini-metric"><div class="v red">{{ upCount }}↑ {{ downCount }}↓</div><div class="l">进步/退步</div></div></el-col>
              <el-col :span="4"><div class="mini-metric"><div class="v orange">{{ examReport.critical.excellence.length + examReport.critical.pass.length }}</div><div class="l">临界生</div></div></el-col>
            </el-row>
            <div ref="subjectRateChartRef" style="height: 220px;"></div>
          </template>
          <el-empty v-else :description="examClassId ? '该班级本学期暂无成绩' : '请选择班级'" :image-size="60" />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="chart-card" style="height: 100%;">
          <h3>超行分榜 <span class="sub-title">（{{ semester || '全部学期' }}）</span></h3>
          <div class="rank-list">
            <div v-for="(r, i) in conductTop" :key="r.student_id" class="rank-item">
              <span class="rank-no" :class="'no-' + (i + 1)">{{ i + 1 }}</span>
              <span class="rank-name">{{ r.student_name }}</span>
              <span class="rank-score" :class="{ positive: r.total_score > 0, negative: r.total_score < 0 }">
                {{ r.total_score > 0 ? '+' : '' }}{{ r.total_score }}
              </span>
            </div>
            <el-empty v-if="!conductTop.length" description="暂无超行分数据" :image-size="50" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 最近作业 + 最近成绩 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <div class="chart-card">
          <h3>最近作业 <span class="sub-title">（未归档，按截止时间排序）</span></h3>
          <div class="rank-list">
            <div v-for="hw in recentHomeworks" :key="hw.id" class="rank-item hw-item">
              <el-tag :type="hwStatusMeta(hw).type" size="small" :effect="hw.due_status === 'due_soon' ? 'dark' : 'light'">
                {{ hwStatusMeta(hw).label }}
              </el-tag>
              <span class="rank-name hw-title" :title="hw.title">{{ hw.title }}</span>
              <span class="rank-class">{{ hw.class_name }}{{ hw.subject_name ? '·' + hw.subject_name : '' }}</span>
              <span class="hw-due">{{ hw.due_date ? formatDue(hw.due_date) : '无截止' }}</span>
            </div>
            <el-empty v-if="!recentHomeworks.length" description="暂无进行中的作业" :image-size="50" />
          </div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="chart-card">
          <h3>最近成绩记录</h3>
          <el-table :data="stats.recent_scores" style="width: 100%" max-height="300">
            <el-table-column prop="student_name" label="学生" />
            <el-table-column prop="subject_name" label="科目" />
            <el-table-column prop="score" label="成绩" width="80" />
            <el-table-column prop="exam_type" label="考试类型" width="100" />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const semester = ref('')
const semesters = ref([])
const classes = ref([])
const examClassId = ref(null)
const examReport = ref(null)
const conductTop = ref([])
const recentHomeworks = ref([])

const stats = reactive({
  total_students: 0,
  total_classes: 0,
  total_scores: 0,
  avg_score: 0,
  attendance_rate: 0,
  recent_scores: []
})

const subjectRateChartRef = ref(null)
let subjectRateChart = null

const HW_STATUS = {
  overdue: { label: '已截止', type: 'danger' },
  due_soon: { label: '即将截止', type: 'warning' },
  ongoing: { label: '进行中', type: 'success' },
  no_due: { label: '未设截止', type: 'info' },
  archived: { label: '已归档', type: 'info' }
}
const hwStatusMeta = (hw) => HW_STATUS[hw.due_status] || { label: '—', type: 'info' }

const formatDue = (d) => {
  const dt = new Date(d)
  return `${dt.getMonth() + 1}/${dt.getDate()} ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
}

const upCount = computed(() => (examReport.value?.rankings || []).filter(r => r.rank_change > 0).length)
const downCount = computed(() => (examReport.value?.rankings || []).filter(r => r.rank_change < 0).length)

const loadSemesters = async () => {
  try {
    const data = await api.semesters.list()
    semesters.value = (data || []).map(s => ({ label: s.name, value: s.name }))
    if (semesters.value.length > 0 && !semester.value) {
      semester.value = semesters.value[0].value
    }
  } catch (e) {
    console.error('加载学期失败', e)
  }
}

const loadClasses = async () => {
  try {
    const data = await api.classes.list()
    classes.value = (data || []).filter(c => c.id)
    const own = userStore.classId
    examClassId.value = classes.value.some(c => c.id === own) ? own : classes.value[0]?.id || null
  } catch (e) {
    console.error('加载班级失败', e)
  }
}

const loadStats = async () => {
  try {
    const data = await api.dashboard.getStats({ semester: semester.value || undefined })
    if (data) {
      Object.assign(stats, data)
    }
  } catch (e) {
    console.error('加载统计数据失败', e)
  }
}

// 最近未归档作业（简略信息，作业管理联动）
const loadRecentHomeworks = async () => {
  recentHomeworks.value = []
  try {
    const res = await api.homeworks.list({ archived: false, page: 1, page_size: 5 }) || []
    recentHomeworks.value = res.data || []
  } catch (e) {
    console.error('加载最近作业失败', e)
  }
}

// 最近一场考试的报告摘要
const tryLoadExamReport = async (cid) => {
  const exams = await api.analytics.getExams({
    class_id: cid, semester: semester.value || undefined
  }) || []
  if (!exams.length) return null
  const latest = exams[exams.length - 1]
  return await api.analytics.getExamReport({
    class_id: cid, semester: semester.value, exam_key: latest.key
  })
}

const loadLatestExam = async () => {
  examReport.value = null
  if (!examClassId.value) return
  try {
    examReport.value = await tryLoadExamReport(examClassId.value)
    // 默认班本学期无考试时，自动切换到第一个有考试的班级（免手动挑选）
    if (!examReport.value) {
      for (const c of classes.value) {
        if (c.id === examClassId.value) continue
        const rep = await tryLoadExamReport(c.id)
        if (rep) {
          examReport.value = rep
          examClassId.value = c.id
          break
        }
      }
    }
    updateSubjectRateChart()
  } catch (e) {
    console.error('加载最近考试失败', e)
  }
}

// 超行分榜（当前学期）
const loadConductTop = async () => {
  conductTop.value = []
  try {
    const list = (await api.semesters.list()) || []
    const sem = list.find(s => s.name === semester.value) || list[0]
    if (!sem) return
    const rows = await api.conduct.getSummary({ term_id: sem.id }) || []
    conductTop.value = [...rows].sort((a, b) => b.total_score - a.total_score).slice(0, 6)
  } catch (e) {
    console.error('加载超行分失败', e)
  }
}

// 积分排行 Top5
const loadAll = async () => {
  await Promise.all([loadStats(), loadLatestExam(), loadConductTop(), loadRecentHomeworks()])
}

// 最近考试：各科得分率横向条形图
const updateSubjectRateChart = () => {
  if (!subjectRateChartRef.value || !examReport.value) return
  if (!subjectRateChart) subjectRateChart = echarts.init(subjectRateChartRef.value)
  const subjects = [...(examReport.value.subjects || [])].reverse()
  subjectRateChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const s = subjects[p.dataIndex]
        let html = `<b>${p.name}</b>（满分 ${s.full_score}）<br/>得分率：${s.score_rate}%`
        if (s.grade_avg_entered != null) html += `<br/>年级均分（录入）：${s.grade_avg_entered}`
        return html
      }
    },
    grid: { left: 80, right: 45, top: 10, bottom: 25 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: subjects.map(s => s.subject_name) },
    series: [{
      type: 'bar',
      data: subjects.map(s => s.score_rate),
      barWidth: '55%',
      label: { show: true, position: 'right', formatter: '{c}%' },
      itemStyle: {
        color: (p) => {
          const v = p.value
          return v >= 90 ? '#67c23a' : v >= 80 ? '#409eff' : v >= 60 ? '#e6a23c' : '#f56c6c'
        }
      }
    }]
  })
}

const handleResize = () => {
  subjectRateChart?.resize()
}

onMounted(async () => {
  try {
    await loadSemesters()
    await loadClasses()
    await loadAll()

    window.addEventListener('resize', handleResize)
  } catch (e) {
    console.error('Dashboard初始化失败', e)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  subjectRateChart?.dispose()
})
</script>

<style scoped>
.dashboard {
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
  font-size: 24px;
  font-weight: 600;
}

.stats-row {
  margin-top: 4px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.chart-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.chart-card h3 {
  margin-bottom: 15px;
  color: #303133;
  font-size: 16px;
}

.card-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.card-toolbar h3 { margin-bottom: 0; }

.sub-title { font-size: 12px; color: #909399; font-weight: normal; }

.exam-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 4px 0 12px;
}

.exam-metrics { margin-bottom: 8px; }

.mini-metric {
  text-align: center;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px 4px;
}

.mini-metric .v { font-size: 18px; font-weight: bold; color: #303133; }
.mini-metric .v.blue { color: #409eff; }
.mini-metric .v.green { color: #67c23a; }
.mini-metric .v.orange { color: #e6a23c; }
.mini-metric .v.red { color: #f56c6c; font-size: 14px; }
.mini-metric .l { font-size: 12px; color: #909399; margin-top: 2px; }

.rank-list { display: flex; flex-direction: column; gap: 8px; }

.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.rank-no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #c0c4cc;
  color: white;
  font-size: 12px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.rank-no.no-1 { background: #f56c6c; }
.rank-no.no-2 { background: #e6a23c; }
.rank-no.no-3 { background: #67c23a; }

.rank-name { flex: 1; font-weight: 500; }

.rank-class { font-size: 12px; color: #909399; }

.rank-score { font-weight: bold; color: #303133; }
.rank-score.points { color: #e6a23c; }
.rank-score.positive { color: #67c23a; }
.rank-score.negative { color: #f56c6c; }

.hw-item { gap: 8px; }

.hw-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hw-due {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
}
</style>
