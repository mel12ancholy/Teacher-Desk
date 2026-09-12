<template>
  <div class="attendance">
    <div class="page-header">
      <h1 class="page-title">考勤管理</h1>
      <div>
        <el-select v-model="filterClassId" placeholder="选择班级" clearable style="width: 150px; margin-right: 10px;" @change="loadData">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button :type="viewMode === 'calendar' ? 'primary' : 'default'" @click="viewMode = 'calendar'" style="margin-right: 10px;">
          日历视图
        </el-button>
        <el-button :type="viewMode === 'list' ? 'primary' : 'default'" @click="viewMode = 'list'" style="margin-right: 10px;">
          列表视图
        </el-button>
        <el-button type="success" @click="showBatchDialog = true" style="margin-right: 10px;">
          <el-icon><Upload /></el-icon>
          批量设置
        </el-button>
        <el-button type="warning" @click="handleExcelImport">
          <el-icon><UploadFilled /></el-icon>
          Excel导入
        </el-button>
        <el-button type="info" @click="showAnalysisDialog = true">
          <el-icon><DataAnalysis /></el-icon>
          考勤分析
        </el-button>
        <el-button type="warning" @click="handleExportAttendance" :loading="exportLoading">
          <el-icon><Download /></el-icon>
          导出考勤
        </el-button>
      </div>
    </div>

    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-label">本月应到</div>
          <div class="stat-value">{{ monthlyStats.total }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-label">出勤</div>
          <div class="stat-value" style="color: #67c23a;">{{ monthlyStats.present }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-label">缺勤</div>
          <div class="stat-value" style="color: #f56c6c;">{{ monthlyStats.absent }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-label">出勤率</div>
          <div class="stat-value" style="color: #409eff;">{{ monthlyStats.attendance_rate }}%</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-label">迟到</div>
          <div class="stat-value" style="color: #e6a23c;">{{ monthlyStats.late }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-label">请假</div>
          <div class="stat-value" style="color: #909399;">{{ monthlyStats.leave }}</div>
        </div>
      </el-col>
    </el-row>

    <div v-if="viewMode === 'calendar'">
      <el-calendar v-model="currentDate">
        <template #date-cell="{ data }">
          <div class="calendar-cell">
            <div class="date-number">{{ data.day.split('-').slice(2).join('') }}</div>
            <div v-if="getDayStats(data.day)" class="attendance-summary">
              <el-tag v-if="getDayStats(data.day).present > 0" type="success" size="small">
                出勤 {{ getDayStats(data.day).present }}
              </el-tag>
              <el-tag v-if="getDayStats(data.day).absent > 0" type="danger" size="small">
                缺勤 {{ getDayStats(data.day).absent }}
              </el-tag>
              <el-tag v-if="getDayStats(data.day).late > 0" type="warning" size="small">
                迟到 {{ getDayStats(data.day).late }}
              </el-tag>
            </div>
            <div v-else class="no-attendance">
              <el-button size="small" type="text" @click="openDayAttendance(data.day)">
                录入考勤
              </el-button>
            </div>
          </div>
        </template>
      </el-calendar>
    </div>

    <div v-else>
      <el-table :data="attendances" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="student_name" label="学生" />
        <el-table-column prop="date" label="日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.date) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑考勤' : '录入考勤'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="学生" prop="student_id">
          <el-select v-model="form.student_id" placeholder="选择学生" style="width: 100%;" filterable>
            <el-option v-for="s in students" :key="s.id" :label="`${s.name} (${s.class_name})`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" prop="date">
          <el-date-picker
            v-model="form.date"
            type="datetime"
            placeholder="选择日期"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio label="present">出勤</el-radio>
            <el-radio label="absent">缺勤</el-radio>
            <el-radio label="late">迟到</el-radio>
            <el-radio label="leave">请假</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBatchDialog" title="批量设置考勤" width="700px">
      <el-alert title="功能说明" type="info" :closable="false" style="margin-bottom: 20px;">
        <ol style="margin: 10px 0 0 20px; padding: 0;">
          <li>选择一个班级和日期，为全班学生批量设置考勤</li>
          <li>考勤状态可选：出勤、缺勤、迟到、请假</li>
          <li>已有考勤记录的学生的状态会被更新</li>
        </ol>
      </el-alert>
      <el-form :model="batchForm" label-width="100px">
        <el-form-item label="选择班级">
          <el-select v-model="batchForm.class_id" placeholder="选择班级" style="width: 100%;" @change="loadBatchStudents">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="考勤日期">
          <el-date-picker
            v-model="batchForm.date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="考勤状态">
          <el-radio-group v-model="batchForm.status">
            <el-radio label="present">出勤</el-radio>
            <el-radio label="absent">缺勤</el-radio>
            <el-radio label="late">迟到</el-radio>
            <el-radio label="leave">请假</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="batchForm.remark" type="textarea" placeholder="可选" />
        </el-form-item>
        <el-form-item label="学生预览" v-if="batchForm.class_id">
          <div class="student-preview">
            <span>该班级共有 <strong>{{ batchStudents.length }}</strong> 名学生</span>
            <div class="student-tags">
              <el-tag v-for="s in batchStudents.slice(0, 10)" :key="s.id" size="small" style="margin: 2px;">
                {{ s.name }}
              </el-tag>
              <el-tag v-if="batchStudents.length > 10" size="small">
                +{{ batchStudents.length - 10 }} 人
              </el-tag>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchDialog = false">取消</el-button>
        <el-button type="primary" @click="handleBatchSubmit" :loading="batchLoading">
          确认批量设置
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDayDialog" title="录入当日考勤" width="900px">
      <el-alert :title="`${dayAttendanceDate} 的考勤记录`" type="info" :closable="false" style="margin-bottom: 15px;" />
      
      <div v-if="dayAttendanceStudents.length > 0">
        <el-table :data="dayAttendanceStudents" style="width: 100%" max-height="400">
          <el-table-column prop="name" label="学生姓名" width="120" />
          <el-table-column prop="student_no" label="学号" width="100" />
          <el-table-column label="考勤状态" width="200">
            <template #default="{ row }">
              <el-select v-model="row.status" style="width: 150px;" @change="handleDayAttendanceChange(row)">
                <el-option label="出勤" value="present" />
                <el-option label="缺勤" value="absent" />
                <el-option label="迟到" value="late" />
                <el-option label="请假" value="leave" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="备注">
            <template #default="{ row }">
              <el-input v-model="row.remark" placeholder="备注" size="small" />
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else>
        <el-empty description="该班级没有学生" />
      </div>
      <template #footer>
        <el-button @click="showDayDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveDayAttendance" :loading="dayLoading">
          保存考勤
        </el-button>
      </template>
    </el-dialog>

    <input ref="fileInputRef" type="file" accept=".csv,.xlsx" style="display: none;" @change="handleFileChange" />

    <el-dialog v-model="showAnalysisDialog" title="考勤分析" width="90%" top="5vh">
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, UploadFilled, DataAnalysis, CircleCheck, Warning, AlarmClock, Download } from '@element-plus/icons-vue'
import api from '@/api'
import * as XLSX from 'xlsx'
import * as echarts from 'echarts'

const attendances = ref([])
const classes = ref([])
const students = ref([])
const batchStudents = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const showBatchDialog = ref(false)
const showDayDialog = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const fileInputRef = ref(null)
const viewMode = ref('calendar')
const currentDate = ref(new Date())
const batchLoading = ref(false)
const dayLoading = ref(false)
const dayAttendanceDate = ref('')
const dayAttendanceStudents = ref([])
const dayAttendanceOriginal = ref([])

const filterClassId = ref(null)
const monthlyStats = reactive({
  total: 0,
  present: 0,
  absent: 0,
  late: 0,
  leave: 0,
  attendance_rate: 0
})

const showAnalysisDialog = ref(false)
const activeAnalysisTab = ref('statistics')
const attendanceChartRef = ref(null)
const classComparisonChartRef = ref(null)
const trendChartRef = ref(null)
const exportLoading = ref(false)

const attendanceAnalysis = reactive({
  attendanceRate: 0,
  abnormalCount: 0,
  consecutiveAbsent: 0,
  abnormalStudents: []
})

const handleExportAttendance = async () => {
  try {
    exportLoading.value = true
    
    const params = { page_size: 1000 }
    if (filterClassId.value) {
      params.class_id = filterClassId.value
    }
    const data = await api.attendance.list(params)
    
    let attendanceList = []
    if (Array.isArray(data)) {
      attendanceList = data
    } else if (data && typeof data === 'object') {
      attendanceList = data.data || data.items || []
    }
    
    if (attendanceList.length === 0) {
      ElMessage.warning('没有考勤数据可导出')
      exportLoading.value = false
      return
    }
    
    const exportData = [
      ['学生姓名', '班级', '日期', '考勤状态', '备注']
    ]
    
    attendanceList.forEach(a => {
      const statusText = {
        present: '出勤',
        absent: '缺勤',
        late: '迟到',
        leave: '请假'
      }[a.status] || a.status || ''
      
      exportData.push([
        a.student_name || '',
        a.class_name || '',
        a.date ? a.date.substring(0, 10) : '',
        statusText,
        a.remark || ''
      ])
    })
    
    const ws = XLSX.utils.aoa_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '考勤记录')
    
    const timestamp = new Date().toISOString().slice(0, 10)
    XLSX.writeFile(wb, `考勤记录_${timestamp}.xlsx`)
    
    exportLoading.value = false
    ElMessage.success(`成功导出 ${attendanceList.length} 条考勤记录`)
  } catch (e) {
    exportLoading.value = false
    console.error('导出考勤失败:', e)
    ElMessage.error('导出考勤失败')
  }
}

const calculateAttendanceAnalysis = () => {
  if (!attendances.value || attendances.value.length === 0) {
    attendanceAnalysis.attendanceRate = 0
    attendanceAnalysis.abnormalCount = 0
    attendanceAnalysis.consecutiveAbsent = 0
    attendanceAnalysis.abnormalStudents = []
    return
  }

  const studentStats = {}

  attendances.value.forEach(a => {
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
  const totalRecords = attendances.value.length
  const presentRecords = attendances.value.filter(a => a.status === 'present').length
  attendanceAnalysis.attendanceRate = ((presentRecords / totalRecords) * 100).toFixed(1)

  attendanceAnalysis.abnormalStudents = students.filter(s =>
    s.absent_count > 0 || s.late_count > 0 || s.leave_count > 0
  ).sort((a, b) => (b.absent_count + b.late_count) - (a.absent_count + a.late_count))

  attendanceAnalysis.abnormalCount = attendanceAnalysis.abnormalStudents.length

  let consecutiveAbsentCount = 0
  const consecutiveAbsentStudents = new Set()
  const sortedByDate = [...attendances.value].sort((a, b) => new Date(a.date) - new Date(b.date))

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
  if (!attendanceChartRef.value || !attendances.value.length) return

  const chart = echarts.init(attendanceChartRef.value)

  const statusCounts = {
    present: 0,
    absent: 0,
    late: 0,
    leave: 0
  }

  attendances.value.forEach(a => {
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
  if (!classComparisonChartRef.value || !attendances.value.length) return

  const chart = echarts.init(classComparisonChartRef.value)

  const classStats = {}

  attendances.value.forEach(a => {
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
  if (!trendChartRef.value || !attendances.value.length) return

  const chart = echarts.init(trendChartRef.value)

  const dateStats = {}

  attendances.value.forEach(a => {
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

const form = reactive({
  student_id: null,
  class_id: null,
  date: null,
  status: 'present',
  remark: ''
})

const batchForm = reactive({
  class_id: null,
  date: null,
  status: 'present',
  remark: ''
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const getAuthHeader = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = (data || []).filter(c => c.id)
}

const loadStudents = async () => {
  const data = await api.students.list({ page_size: 1000 })
  students.value = (data?.data || []).filter(s => s.id)
}

const loadBatchStudents = async () => {
  if (!batchForm.class_id) {
    batchStudents.value = []
    return
  }
  batchStudents.value = students.value.filter(s => s.class_id === batchForm.class_id)
}

const loadAttendances = async () => {
  loading.value = true
  try {
    const params = { page_size: 1000 }
    if (filterClassId.value) {
      params.class_id = filterClassId.value
    }
    const data = await api.attendance.list(params)
    
    let attendanceArray = []
    if (Array.isArray(data)) {
      attendanceArray = data
    } else if (data && typeof data === 'object') {
      attendanceArray = data.data || data.items || []
    }
    
    attendances.value = attendanceArray.map(a => ({
      ...a,
      student_name: a.student_name || students.value.find(s => s.id === a.student_id)?.name || ''
    }))
  } catch (e) {
    console.error('加载考勤失败', e)
    attendances.value = []
  } finally {
    loading.value = false
  }
}

const loadMonthlyStats = async () => {
  if (!filterClassId.value) {
    Object.assign(monthlyStats, { total: 0, present: 0, absent: 0, late: 0, leave: 0, attendance_rate: 0 })
    return
  }

  try {
    const startDate = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth(), 1)
    const endDate = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 0)
    
    const params = {
      class_id: filterClassId.value,
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString()
    }
    
    const data = await api.attendance.getClassStats(filterClassId.value, {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString()
    })
    
    if (data) {
      Object.assign(monthlyStats, data)
    }
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

const loadData = async () => {
  await Promise.all([loadAttendances(), loadMonthlyStats()])
  calculateAttendanceAnalysis()
}

const getDayStats = (dateStr) => {
  if (!dateStr || attendances.value.length === 0) return null

  const dayAttendances = attendances.value.filter(a => {
    if (!a.date) return false
    const attDate = new Date(a.date)
    const attDateStr = attDate.toISOString().split('T')[0]
    return attDateStr === dateStr && (!filterClassId.value || a.class_id === filterClassId.value)
  })

  if (dayAttendances.length === 0) return null

  const stats = { present: 0, absent: 0, late: 0, leave: 0 }
  dayAttendances.forEach(a => {
    if (stats.hasOwnProperty(a.status)) {
      stats[a.status]++
    }
  })
  return stats
}

const openDayAttendance = async (dateStr) => {
  if (!filterClassId.value) {
    ElMessage.warning('请先选择班级')
    return
  }

  dayAttendanceDate.value = dateStr
  dayAttendanceOriginal.value = attendances.value.filter(a => {
    const attDate = new Date(a.date).toISOString().split('T')[0]
    return attDate === dateStr && a.class_id === filterClassId.value
  })

  dayAttendanceStudents.value = students.value
    .filter(s => s.class_id === filterClassId.value)
    .map(s => {
      const existing = dayAttendanceOriginal.value.find(a => a.student_id === s.id)
      return {
        ...s,
        status: existing?.status || 'present',
        remark: existing?.remark || '',
        hasRecord: !!existing
      }
    })

  showDayDialog.value = true
}

const handleDayAttendanceChange = (row) => {
  console.log('考勤状态变更', row)
}

const handleSaveDayAttendance = async () => {
  if (!filterClassId.value || !dayAttendanceDate.value) {
    ElMessage.error('缺少必要参数')
    return
  }

  dayLoading.value = true
  try {
    const attendanceDate = dayAttendanceDate.value
    const token = localStorage.getItem('token')

    const attendanceList = dayAttendanceStudents.value.map(student => ({
      student_no: student.student_no,
      class_id: filterClassId.value,
      date: attendanceDate,
      status: student.status,
      remark: student.remark || ''
    }))

    const response = await fetch('/api/attendance/batch', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ attendances: attendanceList })
    })

    const result = await response.json()

    if (result.success > 0) {
      ElMessage.success(`考勤保存成功！${result.success} 条记录已更新`)
      showDayDialog.value = false
      await loadData()
    } else if (result.errors && result.errors.length > 0) {
      ElMessage.warning(`部分保存失败: ${result.errors[0]}`)
      await loadData()
    } else {
      ElMessage.error('保存失败')
    }
  } catch (e) {
    console.error('保存失败', e)
    ElMessage.error('保存失败')
  } finally {
    dayLoading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, {
    student_id: null,
    class_id: filterClassId.value || classes.value[0]?.id,
    date: null,
    status: 'present',
    remark: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    student_id: row.student_id,
    class_id: row.class_id,
    date: row.date,
    status: row.status,
    remark: row.remark
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该考勤记录吗?', '提示', { type: 'warning' })
    await api.attendance.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      await api.attendance.update(editingId.value, form)
      ElMessage.success('修改成功')
    } else {
      await api.attendance.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleBatchSubmit = async () => {
  if (!batchForm.class_id) {
    ElMessage.warning('请选择班级')
    return
  }
  if (!batchForm.date) {
    ElMessage.warning('请选择日期')
    return
  }

  batchLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/attendance/class-batch', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(batchForm)
    })

    const result = await response.json()
    if (result.success > 0) {
      ElMessage.success(result.message || `成功设置 ${result.success} 名学生`)
      showBatchDialog.value = false
      batchForm.class_id = null
      batchForm.date = null
      batchForm.status = 'present'
      batchForm.remark = ''
      await loadData()
    } else {
      ElMessage.error(result.errors?.[0] || '批量设置失败')
    }
  } catch (e) {
    ElMessage.error('批量设置失败')
  } finally {
    batchLoading.value = false
  }
}

const handleExcelImport = () => {
  fileInputRef.value?.click()
}

const handleFileChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[firstSheetName]
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })

      if (jsonData.length < 2) {
        ElMessage.warning('文件中没有数据')
        return
      }

      const header = jsonData[0].map(h => String(h).trim())
      const rows = jsonData.slice(1).filter(row => row.some(cell => cell !== undefined && cell !== null && cell !== ''))

      const attendanceList = rows.map(row => {
        const getValue = (index) => row[index] !== undefined ? String(row[index]).trim() : ''
        
        return {
          student_no: getValue(header.indexOf('学号')),
          date: getValue(header.indexOf('日期')),
          status: getValue(header.indexOf('状态')) === '缺勤' ? 'absent' : 
                 getValue(header.indexOf('状态')) === '迟到' ? 'late' : 
                 getValue(header.indexOf('状态')) === '请假' ? 'leave' : 'present',
          remark: getValue(header.indexOf('备注'))
        }
      }).filter(a => a.student_no)

      if (attendanceList.length === 0) {
        ElMessage.warning('没有有效的考勤数据')
        return
      }

      if (!filterClassId.value) {
        ElMessage.warning('请先选择班级')
        return
      }

      const token = localStorage.getItem('token')
      const response = await fetch('/api/attendance/batch', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          attendances: attendanceList.map(a => ({
            ...a,
            class_id: filterClassId.value
          }))
        })
      })

      const result = await response.json()
      if (result.success > 0) {
        ElMessage.success(`成功导入 ${result.success} 条考勤记录`)
        await loadData()
      }
      if (result.failed > 0) {
        ElMessage.warning(`${result.failed} 条导入失败`)
      }
    } catch (err) {
      console.error('Excel解析失败', err)
      ElMessage.error('文件解析失败')
    }
  }
  reader.readAsArrayBuffer(file)
  event.target.value = ''
}

const getStatusType = (status) => {
  const types = {
    present: 'success',
    absent: 'danger',
    late: 'warning',
    leave: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    present: '出勤',
    absent: '缺勤',
    late: '迟到',
    leave: '请假'
  }
  return texts[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

watch([filterClassId, currentDate], () => {
  loadData()
})

watch(() => showAnalysisDialog.value, (newVal) => {
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

onMounted(async () => {
  await Promise.all([loadClasses(), loadStudents()])
  loadData()
})
</script>

<style scoped>
.attendance {
  padding: 20px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

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
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #333;
}

.calendar-cell {
  height: 100%;
  padding: 5px;
}

.date-number {
  font-weight: bold;
  margin-bottom: 5px;
}

.attendance-summary {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.no-attendance {
  margin-top: 5px;
}

.student-preview {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
}

.student-tags {
  margin-top: 10px;
}

.table-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
</style>
