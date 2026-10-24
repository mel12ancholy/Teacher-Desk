<template>
  <div class="student-analysis">
    <div class="student-select-row">
      <el-select v-model="selectedStudent" placeholder="选择学生（必选）" style="width: 200px;" filterable @change="tryFetchAnalysis">
        <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
    </div>

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
              <div class="chart-header">
                <span>成绩趋势（班级排名）</span>
                <el-select v-model="trendExamKeys" multiple collapse-tags size="small" style="width: 260px;"
                  placeholder="选择要显示的考试（默认全部）" @change="initTrendChart">
                  <el-option v-for="e in analysis.exams" :key="e.key" :label="e.label" :value="e.key" />
                </el-select>
              </div>
            </template>
            <div ref="trendChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <div class="chart-header">
                <span>科目分析（单次考试）</span>
                <el-select v-model="selectedExamKey" size="small" style="width: 240px;" placeholder="选择一场考试" @change="initSubjectChart">
                  <el-option v-for="e in analysis.exams" :key="e.key" :label="e.label" :value="e.key" />
                </el-select>
              </div>
            </template>
            <div ref="subjectChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="12">
          <el-card>
            <template #header>科目对比（本学期所有考试，含满分与得分率）</template>
            <el-table :data="analysis.subject_analysis" style="width: 100%;" size="small">
              <el-table-column prop="subject_name" label="科目" />
              <el-table-column prop="full_score" label="满分" width="60" align="center" />
              <el-table-column prop="avg_score" label="平均分" width="75" />
              <el-table-column prop="score_rate" label="得分率" width="75">
                <template #default="{ row }">{{ row.score_rate }}%</template>
              </el-table-column>
              <el-table-column prop="max_score" label="最高分" width="70" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <span style="color: #f56c6c;">⚠️ 薄弱科目（得分率低于个人平均 5 个百分点以上）</span>
            </template>
            <div v-if="analysis.weak_subjects?.length > 0">
              <div v-for="(item, idx) in analysis.weak_subjects" :key="item.subject_id" class="weak-item">
                <span>{{ item.subject_name }}</span>
                <el-tag v-if="idx === 0" type="danger" size="small" effect="dark">重点关注</el-tag>
                <span class="score">{{ item.avg_score }}分 / 得分率 {{ item.score_rate }}%</span>
                <span class="gap">低于个人平均 {{ item.gap }} 个百分点</span>
              </div>
            </div>
            <el-empty v-else description="暂无薄弱科目，各科发展均衡" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-empty v-else-if="!loading" description="请选择学生后查看个人成绩分析" />

    <!-- 单科多人趋势（原「班级排名」页能力迁移） -->
    <el-card class="trend-compare-card">
      <template #header>
        <div class="chart-header">
          <span>单科多人趋势对比</span>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <el-select v-model="compareSubjectId" placeholder="科目" style="width: 120px;" @change="loadCompareTrend">
              <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
            <el-select v-model="compareStudentIds" multiple collapse-tags filterable placeholder="选择学生（可多选）" style="width: 260px;" @change="loadCompareTrend">
              <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </div>
        </div>
      </template>
      <div ref="compareChartRef" style="height: 360px;"></div>
      <div v-if="compareEmpty" class="trend-empty-tip">请选择科目和学生后查看多人单科成绩对比</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const props = defineProps({
  students: { type: Array, default: () => [] },
  semester: { type: String, required: true },
  classId: { type: [Number, String], default: null },
  // 从成绩管理页继承的科目（预选单科多人趋势）
  defaultSubjectId: { type: Number, default: null }
})

const subjects = ref([])
const selectedStudent = ref(null)
const selectedExamKey = ref('')
const trendExamKeys = ref([])
const analysis = ref(null)
const loading = ref(false)

const trendChartRef = ref()
const subjectChartRef = ref()
let trendChart = null
let subjectChart = null

// 单科多人趋势
const compareSubjectId = ref(null)
const compareStudentIds = ref([])
const compareChartRef = ref()
const compareEmpty = ref(true)
let compareChart = null

const tryFetchAnalysis = () => {
  if (selectedStudent.value && props.semester) {
    fetchAnalysis()
  } else {
    analysis.value = null
  }
}

const fetchAnalysis = async () => {
  if (!selectedStudent.value || !props.semester) return

  loading.value = true
  try {
    const data = await api.analytics.getStudentAnalysis(selectedStudent.value, { semester: props.semester })
    analysis.value = data

    // 默认：科目分析选最新一次考试；成绩趋势默认显示全部考试
    const exams = analysis.value?.exams || []
    selectedExamKey.value = exams.length ? exams[exams.length - 1].key : ''
    trendExamKeys.value = exams.map(e => e.key)

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

// 成绩趋势：仅绘制勾选的考试（班级排名折线）
const initTrendChart = () => {
  if (!trendChartRef.value || !analysis.value) return

  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendChartRef.value)

  const keySet = new Set(trendExamKeys.value)
  const trend = (analysis.value.rank_trend || []).filter(t => keySet.has(t.key))
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
        return `<b>${p.axisValue}</b><br/>班级排名：第 ${item.rank} 名 / ${item.class_student_count} 人<br/>折算总分：${item.total_score}`
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

// 科目分析：单选一场考试的各科成绩（按该科满分分档着色）
const initSubjectChart = () => {
  if (!subjectChartRef.value || !analysis.value) return

  if (subjectChart) subjectChart.dispose()
  subjectChart = echarts.init(subjectChartRef.value)

  const exam = (analysis.value.exam_details || []).find(e => e.key === selectedExamKey.value)
  const subjectScores = exam?.subject_scores || {}

  // 该生各科满分（从科目分析取）
  const fullByName = {}
  ;(analysis.value.subject_analysis || []).forEach(s => { fullByName[s.subject_name] = s.full_score || 100 })

  const names = Object.keys(subjectScores)
  if (!names.length) {
    subjectChart.setOption({
      title: { text: '暂无考试数据', left: 'center', top: 'middle', textStyle: { color: '#909399', fontSize: 14 } }
    })
    return
  }

  subjectChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const full = fullByName[p.name] || 100
        return `<b>${p.name}</b><br/>成绩：${p.value} / ${full}<br/>得分率：${(p.value / full * 100).toFixed(1)}%`
      }
    },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', min: 0 },
    series: [{
      data: names.map(n => subjectScores[n]),
      type: 'bar',
      barWidth: '50%',
      itemStyle: {
        color: (params) => {
          const pct = params.value / (fullByName[names[params.dataIndex]] || 100) * 100
          return pct >= 90 ? '#67c23a' : pct >= 80 ? '#409eff' : pct >= 60 ? '#e6a23c' : '#f56c6c'
        }
      },
      label: { show: true, position: 'top' }
    }]
  })
}

// ===== 单科多人趋势 =====
const loadSubjects = async () => {
  try {
    subjects.value = (await api.subjects.list()) || []
    if (props.defaultSubjectId && subjects.value.some(s => s.id === props.defaultSubjectId)) {
      compareSubjectId.value = props.defaultSubjectId
    } else if (subjects.value.length) {
      compareSubjectId.value = subjects.value[0].id
    }
  } catch (e) {
    console.error('获取科目失败', e)
  }
}

const loadCompareTrend = async () => {
  const classId = props.classId || props.students[0]?.class_id
  const ready = classId && compareSubjectId.value && compareStudentIds.value.length > 0 && props.semester
  if (!ready) {
    compareEmpty.value = true
    renderCompareChart({ exams: [], students: [] })
    return
  }
  try {
    const data = await api.analytics.getSubjectTrend({
      class_id: classId,
      semesters: props.semester,
      subject_id: compareSubjectId.value,
      student_ids: compareStudentIds.value.join(',')
    })
    compareEmpty.value = !(data?.students || []).length
    renderCompareChart(data || { exams: [], students: [] })
  } catch (e) {
    console.error('查询单科趋势失败', e)
  }
}

const renderCompareChart = (data) => {
  if (!compareChartRef.value) return
  if (!compareChart) compareChart = echarts.init(compareChartRef.value)

  const exams = data.exams || []
  const students = data.students || []
  const subjectName = subjects.value.find(s => s.id === compareSubjectId.value)?.name || ''

  const series = students.map(stu => ({
    name: stu.student_name,
    type: 'line',
    data: stu.scores,
    smooth: true,
    connectNulls: false,
    symbolSize: 8
  }))

  compareChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const lines = [`<b>${params[0]?.axisValue || ''}</b>`]
        params.forEach(p => {
          lines.push(`${p.marker} ${p.seriesName}：${p.value == null ? '无成绩' : p.value} 分`)
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
      min: 0
    },
    series
  }, true)
}

const handleResize = () => {
  trendChart?.resize()
  subjectChart?.resize()
  compareChart?.resize()
}

window.addEventListener('resize', handleResize)

onMounted(() => {
  loadSubjects()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  subjectChart?.dispose()
  compareChart?.dispose()
})
</script>

<style scoped>
.student-select-row { margin-bottom: 16px; }

.stats-row { margin-bottom: 20px; }

.stat-item { text-align: center; padding: 10px 0; }

.stat-number { font-size: 28px; font-weight: bold; color: #409eff; }
.stat-number.danger { color: #f56c6c; }

.stat-label { font-size: 14px; color: #909399; margin-top: 5px; }

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-card { margin-bottom: 20px; }

.weak-item {
  display: flex;
  align-items: center;
  padding: 10px;
  background: #fef0f0;
  border-radius: 4px;
  margin-bottom: 8px;
  gap: 10px;
}

.weak-item span:first-child { flex: 1; font-weight: 500; }

.weak-item .score { color: #f56c6c; font-weight: bold; margin-right: 10px; }

.weak-item .gap { color: #909399; font-size: 12px; }

.trend-compare-card { margin-top: 20px; }

.trend-empty-tip {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 12px 0;
}
</style>
