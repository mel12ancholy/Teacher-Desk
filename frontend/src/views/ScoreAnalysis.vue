<template>
  <div class="score-analysis">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>成绩分析</span>
              <div class="header-actions">
                <el-select v-model="selectedClass" placeholder="选择班级（必选）" style="width: 150px;" @change="onClassChange">
                  <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
                <el-select v-model="selectedStudent" placeholder="选择学生（必选）" style="width: 150px;" :disabled="!selectedClass" @change="tryFetchAnalysis">
                  <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
                </el-select>
                <el-select v-model="semester" placeholder="选择学期（必选）" style="width: 140px;" @change="onSemesterChange">
                  <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
                </el-select>
              </div>
            </div>
          </template>

          <div v-if="analysis" class="analysis-content" v-loading="loading">
            <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px;"
              :title="`${analysis.student?.name} - ${analysis.student?.class_name} - ${semester}`" />

            <el-row :gutter="20" class="stats-row">
              <el-col :span="8">
                <el-card shadow="hover">
                  <div class="stat-item">
                    <div class="stat-number danger">{{ analysis.summary?.min_score ?? '-' }}</div>
                    <div class="stat-label">历史最低（{{ analysis.summary?.min_score_subject || '-' }}）</div>
                  </div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card shadow="hover">
                  <div class="stat-item">
                    <div class="stat-number">{{ analysis.summary?.max_score ?? '-' }}</div>
                    <div class="stat-label">最高成绩（{{ analysis.summary?.max_score_subject || '-' }}）</div>
                  </div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card shadow="hover">
                  <div class="stat-item">
                    <div class="stat-number">{{ analysis.summary?.total_exams ?? 0 }}</div>
                    <div class="stat-label">考试次数</div>
                  </div>
                </el-card>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-card class="chart-card">
                  <template #header>
                    <span>成绩趋势（按考试总分在班级中的排名）</span>
                  </template>
                  <div ref="trendChartRef" style="height: 300px;"></div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card class="chart-card">
                  <template #header>
                    <div class="chart-header">
                      <span>科目分析（单次考试）</span>
                      <el-radio-group v-model="selectedExamKey" size="small" @change="initSubjectChart">
                        <el-radio-button v-for="e in analysis.exams" :key="e.key" :value="e.key">
                          {{ e.label }}
                        </el-radio-button>
                      </el-radio-group>
                    </div>
                  </template>
                  <div ref="subjectChartRef" style="height: 300px;"></div>
                </el-card>
              </el-col>
            </el-row>

            <el-row :gutter="20" style="margin-top: 20px;">
              <el-col :span="12">
                <el-card>
                  <template #header>科目对比（本学期所有考试的科目成绩）</template>
                  <el-table :data="analysis.subject_analysis" style="width: 100%;" size="small">
                    <el-table-column prop="subject_name" label="科目" />
                    <el-table-column prop="avg_score" label="平均分" />
                    <el-table-column prop="max_score" label="最高分" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>
                    <span style="color: #f56c6c;">⚠️ 薄弱科目（平均分低于个人总体平均 5 分以上）</span>
                  </template>
                  <div v-if="analysis.weak_subjects?.length > 0">
                    <div v-for="(item, idx) in analysis.weak_subjects" :key="item.subject_id" class="weak-item">
                      <span>{{ item.subject_name }}</span>
                      <el-tag v-if="idx === 0" type="danger" size="small" effect="dark">重点关注</el-tag>
                      <span class="score">{{ item.avg_score }}分</span>
                      <span class="gap">低于个人平均 {{ item.gap }}分</span>
                    </div>
                  </div>
                  <el-empty v-else description="暂无薄弱科目，各科发展均衡" :image-size="60" />
                </el-card>
              </el-col>
            </el-row>
          </div>

          <el-empty v-else-if="!loading" description="请选择班级、学生和学期后查看成绩分析" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;" v-if="selectedClass && semester">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>班级成绩分析 - {{ getClassName() }}（{{ semester }}）</span>
          </template>
          <div ref="classChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const trendChartRef = ref()
const subjectChartRef = ref()
const classChartRef = ref()

let trendChart = null
let subjectChart = null
let classChart = null

const classes = ref([])
const students = ref([])
const semesters = ref([])
const selectedClass = ref(null)
const selectedStudent = ref(null)
const semester = ref('')
const selectedExamKey = ref('')

const analysis = ref(null)
const loading = ref(false)
const classAnalysis = ref(null)

const fetchClasses = async () => {
  try {
    const data = await api.classes.list()
    classes.value = data || []
  } catch (e) {
    console.error('获取班级失败', e)
  }
}

const fetchSemesters = async () => {
  try {
    const data = await api.semesters.list()
    semesters.value = data || []
    // 学期必选：默认最新学期（学期管理按 year/name 倒序返回）
    if (semesters.value.length) {
      semester.value = semesters.value[0].name
    }
  } catch (e) {
    console.error('获取学期失败', e)
  }
}

const loadClassAnalysis = async () => {
  if (!selectedClass.value || !semester.value) return
  try {
    const classData = await api.analytics.getClassAnalysis(selectedClass.value, { semester: semester.value })
    classAnalysis.value = classData
    nextTick(() => initClassChart())
  } catch (e) {
    console.error('获取班级分析失败', e)
  }
}

const onClassChange = async () => {
  selectedStudent.value = null
  students.value = []
  analysis.value = null

  if (selectedClass.value) {
    try {
      const data = await api.students.list({ class_id: selectedClass.value, page: 1, page_size: 1000 })
      students.value = data?.data || []
    } catch (e) {
      console.error('获取学生失败', e)
    }
    loadClassAnalysis()
  } else {
    classAnalysis.value = null
  }
}

const onSemesterChange = () => {
  loadClassAnalysis()
  tryFetchAnalysis()
}

// 班级、学生、学期三个控件必选，选齐后自动出数据
const tryFetchAnalysis = () => {
  if (selectedClass.value && selectedStudent.value && semester.value) {
    fetchAnalysis()
  } else {
    analysis.value = null
  }
}

const fetchAnalysis = async () => {
  if (!selectedStudent.value || !semester.value) return

  loading.value = true
  try {
    const data = await api.analytics.getStudentAnalysis(selectedStudent.value, { semester: semester.value })
    analysis.value = data

    // 默认选中最新一次考试
    const exams = analysis.value?.exams || []
    selectedExamKey.value = exams.length ? exams[exams.length - 1].key : ''

    nextTick(() => {
      initTrendChart()
      initSubjectChart()
    })
  } catch (e) {
    console.error('获取分析失败', e)
  } finally {
    loading.value = false
  }
}

const getClassName = () => {
  const cls = classes.value.find(c => c.id === selectedClass.value)
  return cls ? cls.name : ''
}

// 成绩趋势：该学期每次考试按总分在班级中的排名变化（排名靠前显示在上方）
const initTrendChart = () => {
  if (!trendChartRef.value || !analysis.value) return

  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendChartRef.value)

  const trend = analysis.value.rank_trend || []
  if (!trend.length) {
    trendChart.setOption({
      title: { text: '暂无考试数据', left: 'center', top: 'middle', textStyle: { color: '#909399', fontSize: 14 } }
    })
    return
  }

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const item = trend[p.dataIndex]
        return `<b>${p.axisValue}</b><br/>班级排名：第 ${item.rank} 名 / ${item.class_student_count} 人<br/>本次考试总分：${item.total_score}`
      }
    },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: trend.map(t => t.label),
      axisLabel: { rotate: 25 }
    },
    yAxis: {
      type: 'value',
      name: '班级排名',
      inverse: true,
      minInterval: 1
    },
    series: [{
      data: trend.map(t => t.rank),
      type: 'line',
      smooth: true,
      symbolSize: 9,
      label: { show: true, position: 'top', formatter: '第{c}名' },
      lineStyle: { width: 3 },
      itemStyle: { color: '#409eff' },
      areaStyle: { opacity: 0.15 }
    }]
  })
}

// 科目分析：单次考试的各科成绩
const initSubjectChart = () => {
  if (!subjectChartRef.value || !analysis.value) return

  if (subjectChart) subjectChart.dispose()
  subjectChart = echarts.init(subjectChartRef.value)

  const exam = (analysis.value.exam_details || []).find(e => e.key === selectedExamKey.value)
  const subjectScores = exam?.subject_scores || {}

  const names = Object.keys(subjectScores)
  if (!names.length) {
    subjectChart.setOption({
      title: { text: '暂无考试数据', left: 'center', top: 'middle', textStyle: { color: '#909399', fontSize: 14 } }
    })
    return
  }

  subjectChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', min: 0 },
    series: [{
      data: names.map(n => subjectScores[n]),
      type: 'bar',
      barWidth: '50%',
      itemStyle: {
        color: (params) => {
          const v = params.value
          return v >= 90 ? '#67c23a' : v >= 80 ? '#409eff' : v >= 60 ? '#e6a23c' : '#f56c6c'
        }
      },
      label: { show: true, position: 'top' }
    }]
  })
}

const initClassChart = () => {
  if (!classChartRef.value || !classAnalysis.value?.score_distribution) return

  if (classChart) classChart.dispose()
  classChart = echarts.init(classChartRef.value)

  const dist = classAnalysis.value.score_distribution || {}

  classChart.setOption({
    tooltip: {},
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}: {c}人' },
      data: [
        { value: dist.excellent || 0, name: '优秀(≥90)', itemStyle: { color: '#67c23a' } },
        { value: dist.good || 0, name: '良好(80-89)', itemStyle: { color: '#409eff' } },
        { value: dist.average || 0, name: '中等(70-79)', itemStyle: { color: '#e6a23c' } },
        { value: dist.pass || 0, name: '及格(60-69)', itemStyle: { color: '#909399' } },
        { value: dist.fail || 0, name: '不及格(<60)', itemStyle: { color: '#f56c6c' } }
      ]
    }]
  })
}

const handleResize = () => {
  trendChart?.resize()
  subjectChart?.resize()
  classChart?.resize()
}

onMounted(async () => {
  await Promise.all([fetchClasses(), fetchSemesters()])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  subjectChart?.dispose()
  classChart?.dispose()
})

window.addEventListener('resize', handleResize)
</script>

<style scoped>
.score-analysis { padding: 20px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 10px 0;
}

.stat-number {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.stat-number.danger {
  color: #f56c6c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.chart-card {
  margin-bottom: 20px;
}

.weak-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background: #fef0f0;
  border-radius: 4px;
  margin-bottom: 8px;
  gap: 10px;
}

.weak-item span:first-child {
  flex: 1;
  font-weight: 500;
}

.weak-item .score {
  color: #f56c6c;
  font-weight: bold;
  margin-right: 10px;
}

.weak-item .gap {
  color: #909399;
  font-size: 12px;
}
</style>
