<template>
  <el-dialog
    :model-value="modelValue"
    title="考勤分析"
    width="90%"
    top="5vh"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-tabs v-model="activeAnalysisTab">
      <el-tab-pane label="考勤统计" name="statistics">
        <el-row :gutter="20" style="margin-bottom: 20px;">
          <el-col :span="8">
            <div class="analysis-stat-card">
              <div class="analysis-stat-icon" style="background: rgba(103, 194, 58, 0.1);">
                <el-icon style="font-size: 24px; color: #67c23a;"><CircleCheck /></el-icon>
              </div>
              <div class="analysis-stat-content">
                <div class="analysis-stat-label">出勤率</div>
                <div class="analysis-stat-value" style="color: #67c23a;">{{ attendanceAnalysis.attendanceRate }}%</div>
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="analysis-stat-card">
              <div class="analysis-stat-icon" style="background: rgba(245, 108, 108, 0.1);">
                <el-icon style="font-size: 24px; color: #f56c6c;"><Warning /></el-icon>
              </div>
              <div class="analysis-stat-content">
                <div class="analysis-stat-label">异常考勤</div>
                <div class="analysis-stat-value" style="color: #f56c6c;">{{ attendanceAnalysis.abnormalCount }}</div>
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="analysis-stat-card">
              <div class="analysis-stat-icon" style="background: rgba(230, 162, 60, 0.1);">
                <el-icon style="font-size: 24px; color: #e6a23c;"><AlarmClock /></el-icon>
              </div>
              <div class="analysis-stat-content">
                <div class="analysis-stat-label">连续缺勤学生</div>
                <div class="analysis-stat-value" style="color: #e6a23c;">{{ attendanceAnalysis.consecutiveAbsent }}</div>
              </div>
            </div>
          </el-col>
        </el-row>
        <div ref="attendanceChartRef" class="chart-container"></div>
      </el-tab-pane>

      <el-tab-pane label="考勤异常" name="abnormal">
        <el-alert
          v-if="attendanceAnalysis.abnormalStudents.length > 0"
          :title="`发现 ${attendanceAnalysis.abnormalStudents.length} 名学生存在考勤异常`"
          type="warning"
          :closable="false"
          style="margin-bottom: 20px;"
        />
        <el-table v-if="attendanceAnalysis.abnormalStudents.length > 0" :data="attendanceAnalysis.abnormalStudents" border stripe>
          <el-table-column prop="student_name" label="学生姓名" />
          <el-table-column prop="absent_count" label="缺勤次数" width="120">
            <template #default="{ row }">
              <el-tag type="danger">{{ row.absent_count }} 次</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="late_count" label="迟到次数" width="120">
            <template #default="{ row }">
              <el-tag type="warning">{{ row.late_count }} 次</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="leave_count" label="请假次数" width="120">
            <template #default="{ row }">
              <el-tag type="info">{{ row.leave_count }} 次</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="viewStudentAttendance(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无考勤异常记录" />
      </el-tab-pane>

      <el-tab-pane label="班级对比" name="comparison">
        <div ref="classComparisonChartRef" class="chart-container"></div>
      </el-tab-pane>

      <el-tab-pane label="考勤趋势" name="trend">
        <div ref="trendChartRef" class="chart-container"></div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, watch, nextTick } from 'vue'
import { ElMessageBox } from 'element-plus'
import { CircleCheck, Warning, AlarmClock } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  attendances: { type: Array, default: () => [] }
})

defineEmits(['update:modelValue'])

const activeAnalysisTab = ref('statistics')
const attendanceChartRef = ref(null)
const classComparisonChartRef = ref(null)
const trendChartRef = ref(null)

const attendanceAnalysis = reactive({
  attendanceRate: 0,
  abnormalCount: 0,
  consecutiveAbsent: 0,
  abnormalStudents: []
})

const calculateAttendanceAnalysis = () => {
  if (!props.attendances || props.attendances.length === 0) {
    attendanceAnalysis.attendanceRate = 0
    attendanceAnalysis.abnormalCount = 0
    attendanceAnalysis.consecutiveAbsent = 0
    attendanceAnalysis.abnormalStudents = []
    return
  }

  const studentStats = {}

  props.attendances.forEach(a => {
    const name = a.student_name || '未知学生'
    if (!studentStats[name]) {
      studentStats[name] = {
        student_name: name,
        absent_count: 0,
        late_count: 0,
        leave_count: 0,
        present_count: 0,
        total: 0
      }
    }
    studentStats[name].total++
    if (a.status === 'absent') studentStats[name].absent_count++
    else if (a.status === 'late') studentStats[name].late_count++
    else if (a.status === 'leave') studentStats[name].leave_count++
    else if (a.status === 'present') studentStats[name].present_count++
  })

  const students = Object.values(studentStats)
  const totalRecords = props.attendances.length
  const presentRecords = props.attendances.filter(a => a.status === 'present').length
  attendanceAnalysis.attendanceRate = ((presentRecords / totalRecords) * 100).toFixed(1)

  attendanceAnalysis.abnormalStudents = students.filter(s =>
    s.absent_count > 0 || s.late_count > 0 || s.leave_count > 0
  ).sort((a, b) => (b.absent_count + b.late_count) - (a.absent_count + a.late_count))

  attendanceAnalysis.abnormalCount = attendanceAnalysis.abnormalStudents.length

  let consecutiveAbsentCount = 0
  const consecutiveAbsentStudents = new Set()
  const sortedByDate = [...props.attendances].sort((a, b) => new Date(a.date) - new Date(b.date))

  for (let i = 1; i < sortedByDate.length; i++) {
    const prev = sortedByDate[i - 1]
    const curr = sortedByDate[i]
    if (prev.student_name === curr.student_name &&
        prev.status === 'absent' &&
        curr.status === 'absent') {
      const prevDate = new Date(prev.date)
      const currDate = new Date(curr.date)
      const diffDays = (currDate - prevDate) / (1000 * 60 * 60 * 24)
      if (diffDays <= 3) {
        consecutiveAbsentStudents.add(prev.student_name)
        consecutiveAbsentStudents.add(curr.student_name)
      }
    }
  }
  attendanceAnalysis.consecutiveAbsent = consecutiveAbsentStudents.size
}

const initAttendanceChart = () => {
  if (!attendanceChartRef.value || !props.attendances.length) return

  const chart = echarts.init(attendanceChartRef.value)

  const statusCounts = {
    present: 0,
    absent: 0,
    late: 0,
    leave: 0
  }

  props.attendances.forEach(a => {
    if (statusCounts.hasOwnProperty(a.status)) {
      statusCounts[a.status]++
    }
  })

  const option = {
    title: {
      text: '考勤状态分布',
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: 0
    },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: statusCounts.present, name: '出勤', itemStyle: { color: '#67c23a' } },
        { value: statusCounts.absent, name: '缺勤', itemStyle: { color: '#f56c6c' } },
        { value: statusCounts.late, name: '迟到', itemStyle: { color: '#e6a23c' } },
        { value: statusCounts.leave, name: '请假', itemStyle: { color: '#909399' } }
      ],
      label: {
        formatter: '{b}: {c} ({d}%)'
      }
    }]
  }

  chart.setOption(option)
}

const initClassComparisonChart = () => {
  if (!classComparisonChartRef.value || !props.attendances.length) return

  const chart = echarts.init(classComparisonChartRef.value)

  const classStats = {}

  props.attendances.forEach(a => {
    const className = a.class_name || '未知班级'
    if (!classStats[className]) {
      classStats[className] = { total: 0, present: 0, absent: 0 }
    }
    classStats[className].total++
    if (a.status === 'present') classStats[className].present++
    else if (a.status === 'absent') classStats[className].absent++
  })

  const classes = Object.keys(classStats)
  const rates = classes.map(c => {
    return ((classStats[c].present / classStats[c].total) * 100).toFixed(1)
  })

  const option = {
    title: {
      text: '各班级出勤率对比',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: classes
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [{
      data: rates,
      type: 'bar',
      itemStyle: {
        color: (params) => {
          const rate = parseFloat(params.value)
          if (rate >= 90) return '#67c23a'
          else if (rate >= 70) return '#e6a23c'
          else return '#f56c6c'
        }
      },
      label: {
        show: true,
        position: 'top',
        formatter: '{c}%'
      }
    }]
  }

  chart.setOption(option)
}

const initTrendChart = () => {
  if (!trendChartRef.value || !props.attendances.length) return

  const chart = echarts.init(trendChartRef.value)

  const dateStats = {}

  props.attendances.forEach(a => {
    const date = a.date ? a.date.substring(0, 10) : '未知日期'
    if (!dateStats[date]) {
      dateStats[date] = { total: 0, present: 0, absent: 0, late: 0 }
    }
    dateStats[date].total++
    if (a.status === 'present') dateStats[date].present++
    else if (a.status === 'absent') dateStats[date].absent++
    else if (a.status === 'late') dateStats[date].late++
  })

  const dates = Object.keys(dateStats).sort()
  const presentRates = dates.map(d => ((dateStats[d].present / dateStats[d].total) * 100).toFixed(1))
  const absentCounts = dates.map(d => dateStats[d].absent)

  const option = {
    title: {
      text: '考勤趋势变化',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['出勤率', '缺勤人数'],
      bottom: 0
    },
    xAxis: {
      type: 'category',
      data: dates
    },
    yAxis: [
      {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      },
      {
        type: 'value',
        min: 0
      }
    ],
    series: [
      {
        name: '出勤率',
        type: 'line',
        data: presentRates,
        smooth: true,
        itemStyle: { color: '#67c23a' }
      },
      {
        name: '缺勤人数',
        type: 'bar',
        data: absentCounts,
        itemStyle: { color: '#f56c6c' }
      }
    ]
  }

  chart.setOption(option)
}

const viewStudentAttendance = (student) => {
  ElMessageBox.alert(
    `<div>
      <p><strong>姓名：</strong>${student.student_name}</p>
      <p><strong>缺勤次数：</strong>${student.absent_count} 次</p>
      <p><strong>迟到次数：</strong>${student.late_count} 次</p>
      <p><strong>请假次数：</strong>${student.leave_count} 次</p>
    </div>`,
    '学生考勤详情',
    {
      confirmButtonText: '确定',
      dangerouslyUseHTMLString: true
    }
  )
}

// 数据变化时重算统计（原实现在 loadData 末尾调用）
watch(() => props.attendances, calculateAttendanceAnalysis, { immediate: true })

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    nextTick(() => {
      initAttendanceChart()
      initClassComparisonChart()
      initTrendChart()
    })
  }
})

watch(() => activeAnalysisTab.value, (newVal) => {
  if (newVal) {
    nextTick(() => {
      if (newVal === 'statistics') {
        initAttendanceChart()
      } else if (newVal === 'comparison') {
        initClassComparisonChart()
      } else if (newVal === 'trend') {
        initTrendChart()
      }
    })
  }
})
</script>

<style scoped>
.analysis-stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s;
}

.analysis-stat-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.analysis-stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.analysis-stat-content {
  flex: 1;
}

.analysis-stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.analysis-stat-value {
  font-size: 28px;
  font-weight: bold;
}

.chart-container {
  width: 100%;
  height: 400px;
  margin-top: 20px;
}
</style>
