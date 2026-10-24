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

    <div v-else class="table-container">
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

    <!-- 录入/编辑单条考勤 -->
    <AttendanceFormDialog
      v-model="dialogVisible"
      :is-edit="isEdit"
      :editing-row="editingRow"
      :students="students"
      :default-class-id="filterClassId"
      @submit="handleSubmit"
    />

    <!-- 批量设置考勤 -->
    <AttendanceBatchDialog
      v-model="showBatchDialog"
      :classes="classes"
      :students="students"
      @saved="loadData"
    />

    <!-- 录入当日考勤 -->
    <AttendanceDayDialog
      v-model="showDayDialog"
      :date="dayAttendanceDate"
      :class-id="filterClassId"
      :students="students"
      :attendances="attendances"
      @saved="loadData"
    />

    <!-- 考勤分析 -->
    <AttendanceAnalysisDialog
      v-model="showAnalysisDialog"
      :attendances="attendances"
    />

    <input ref="fileInputRef" type="file" accept=".csv,.xlsx" style="display: none;" @change="handleFileChange" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled, DataAnalysis, Download } from '@element-plus/icons-vue'
import api from '@/api'
import * as XLSX from 'xlsx'
import AttendanceFormDialog from '@/components/attendance/AttendanceFormDialog.vue'
import AttendanceBatchDialog from '@/components/attendance/AttendanceBatchDialog.vue'
import AttendanceDayDialog from '@/components/attendance/AttendanceDayDialog.vue'
import AttendanceAnalysisDialog from '@/components/attendance/AttendanceAnalysisDialog.vue'

const attendances = ref([])
const classes = ref([])
const students = ref([])
const loading = ref(false)
const exportLoading = ref(false)
const fileInputRef = ref(null)
const viewMode = ref('calendar')
const currentDate = ref(new Date())

// 弹窗状态
const dialogVisible = ref(false)
const showBatchDialog = ref(false)
const showDayDialog = ref(false)
const showAnalysisDialog = ref(false)
const isEdit = ref(false)
const editingRow = ref(null)
const dayAttendanceDate = ref('')

const filterClassId = ref(null)
const monthlyStats = reactive({
  total: 0,
  present: 0,
  absent: 0,
  late: 0,
  leave: 0,
  attendance_rate: 0
})

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = (data || []).filter(c => c.id)
}

const loadStudents = async () => {
  const data = await api.students.list({ page_size: 1000 })
  students.value = (data?.data || []).filter(s => s.id)
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

const openDayAttendance = (dateStr) => {
  if (!filterClassId.value) {
    ElMessage.warning('请先选择班级')
    return
  }
  dayAttendanceDate.value = dateStr
  showDayDialog.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editingRow.value = row
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

const handleSubmit = async (formData) => {
  try {
    if (isEdit.value) {
      await api.attendance.update(editingRow.value.id, formData)
      ElMessage.success('修改成功')
    } else {
      await api.attendance.create(formData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    ElMessage.error('操作失败')
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

onMounted(async () => {
  await Promise.all([loadClasses(), loadStudents()])
  loadData()
})
</script>

<style scoped>
.attendance {
  padding: 20px;
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

.table-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
</style>
