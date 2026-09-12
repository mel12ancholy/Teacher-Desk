<template>
  <div class="seating-page">
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="toolbar-label">班级：</span>
          <el-select v-model="classId" style="width: 160px" @change="handleClassChange" :disabled="viewingHistory">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <span class="toolbar-label">行数：</span>
          <el-select v-model="rowCount" style="width: 90px" @change="handleGridResize" :disabled="viewingHistory">
            <el-option v-for="r in rowOptions" :key="r" :label="r" :value="r" />
          </el-select>
          <span class="toolbar-label">列数：</span>
          <el-select v-model="columnCount" style="width: 90px" @change="handleGridResize" :disabled="viewingHistory">
            <el-option v-for="c in columnOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <div class="toolbar-right">
          <el-button type="warning" @click="handleRandomSeating" :disabled="!canRandom">随机排序</el-button>
          <el-button type="primary" @click="handleSave" :disabled="viewingHistory">保存</el-button>
          <el-button @click="triggerImport" :disabled="!canImport">导入</el-button>
          <el-button @click="handleExport" :disabled="viewingHistory">导出</el-button>
          <el-button type="danger" plain @click="handleClear" :disabled="viewingHistory">清除</el-button>
        </div>
      </div>
      <input ref="fileInputRef" type="file" accept=".xlsx,.xls,.csv" style="display: none" @change="handleFileChange" />
    </el-card>

    <el-alert v-if="viewingHistory" type="info" :closable="false" show-icon class="history-alert"
      :title="`正在查看 ${historyDate} 的历史座位（只读），返回「编辑今天」后可修改`" />
    <el-alert v-if="!viewingHistory && !loading" type="success" :closable="false" show-icon class="history-alert"
      :title="`当前编辑 ${today} 的座位表`" />

    <div class="main-area">
      <el-card shadow="never" class="unseated-card" :body-style="{ padding: '12px' }">
        <template #header>
          <div class="card-header">
            <span>未排座学生（{{ unseatedStudents.length }}）</span>
            <el-tag size="small" type="info">可拖拽</el-tag>
          </div>
        </template>
        <div class="unseated-list" @dragover.prevent @drop="handleDropOnUnseated">
          <el-empty v-if="unseatedStudents.length === 0" description="暂无未排座学生" :image-size="60" />
          <div v-for="(stu, idx) in unseatedStudents" :key="`${stu.student_id ?? 'x'}-${idx}`" class="unseated-item"
            draggable="true" @dragstart="handleUnseatedDragStart($event, idx)" @dragend="handleDragEnd">
            {{ stu.student_name }}
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="seat-card" :body-style="{ padding: '12px' }">
        <template #header>
          <div class="card-header">
            <span>座位表（{{ displayRowCount }} 行 × {{ displayColumnCount }} 列）</span>
            <span class="seat-hint">{{ viewingHistory ? '历史数据，只读' : '拖拽学生到座位，学生之间自动交换' }}</span>
          </div>
        </template>
        <div class="seat-area">
          <div class="seat-grid" :style="gridStyle">
            <template v-for="r in displayRowCount" :key="r">
              <div v-for="c in displayColumnCount" :key="`${r}-${c}`" class="seat-cell"
                :class="{ 'seat-cell-filled': !!seatAt(r, c), 'drag-over': dragOverSeat === `${r}-${c}` }"
                :draggable="!!seatAt(r, c) && !viewingHistory"
                @dragstart="handleSeatDragStart($event, r, c)"
                @dragend="handleDragEnd"
                @dragover.prevent="dragOverSeat = `${r}-${c}`"
                @dragleave="dragOverSeat === `${r}-${c}` && (dragOverSeat = null)"
                @drop="handleDropOnSeat($event, r, c)">
                <span class="seat-pos">{{ r }}-{{ c }}</span>
                <span v-if="seatAt(r, c)" class="seat-name" :style="seatNameStyle">{{ seatAt(r, c).student_name }}</span>
                <el-icon v-else class="seat-empty-icon"><Plus /></el-icon>
              </div>
            </template>
          </div>
          <div class="podium">讲台</div>
        </div>
      </el-card>
    </div>

    <el-card shadow="never" class="history-card" :body-style="{ padding: '12px 20px' }">
      <div class="history-bar">
        <span class="toolbar-label">历史座次：</span>
        <el-select v-model="selectedHistoryDate" placeholder="选择日期查看历史座次" style="width: 200px" clearable
          @change="handleHistoryChange">
          <el-option v-for="d in historyDates" :key="d" :label="d" :value="d" />
        </el-select>
        <el-button v-if="viewingHistory" type="primary" link @click="backToToday">返回编辑今天</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const MIN_ROWS = 4, MAX_ROWS = 12
const MIN_COLUMNS = 4, MAX_COLUMNS = 16
const rowOptions = Array.from({ length: MAX_ROWS - MIN_ROWS + 1 }, (_, i) => i + MIN_ROWS)
const columnOptions = Array.from({ length: MAX_COLUMNS - MIN_COLUMNS + 1 }, (_, i) => i + MIN_COLUMNS)

const classes = ref([])
const classId = ref(null)
const rowCount = ref(6)
const columnCount = ref(8)
const loading = ref(false)
const fileInputRef = ref(null)

// 当前编辑状态（今天）
const seatStudents = ref([])   // [{ student_id, student_name, seat_row, seat_column }]
const unseatedStudents = ref([])  // [{ student_id, student_name }]

// 历史查看状态
const historyDates = ref([])
const selectedHistoryDate = ref('')
const viewingHistory = ref(false)
const historyDate = ref('')
const historyStudents = ref([])

const today = new Date().toISOString().slice(0, 10)

const displayRowCount = computed(() => viewingHistory.value ? historyRowCount.value : rowCount.value)
const displayColumnCount = computed(() => viewingHistory.value ? historyColumnCount.value : columnCount.value)
const historyRowCount = ref(6)
const historyColumnCount = ref(8)

const dragData = ref(null)
const dragOverSeat = ref(null)

// 座位表区域整体尺寸固定，单元格随行列数自动缩放
const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${displayColumnCount.value}, minmax(0, 1fr))`,
  gridTemplateRows: `repeat(${displayRowCount.value}, minmax(0, 1fr))`,
  gap: '4px'
}))

const seatNameStyle = computed(() => {
  // 列数多时缩小字号，避免姓名溢出
  const cols = displayColumnCount.value
  const fontSize = cols > 12 ? 10 : cols > 8 ? 12 : 14
  return { fontSize: `${fontSize}px` }
})

const allStudentCount = computed(() =>
  seatStudents.value.length + unseatedStudents.value.length
)

// 随机排序：仅在已有学生时可用
const canRandom = computed(() =>
  !viewingHistory.value && allStudentCount.value > 0
)

// 导入：仅当前座位表完全没有学生姓名时允许
const canImport = computed(() =>
  !viewingHistory.value && allStudentCount.value === 0
)

const seatAt = (r, c) => {
  const list = viewingHistory.value ? historyStudents.value : seatStudents.value
  return list.find(s => s.seat_row === r && s.seat_column === c) || null
}

// ========== 数据加载 ==========

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = data || []
  if (!classes.value.length) {
    ElMessage.warning('暂无可管理的班级，请联系管理员创建班级')
    return false
  }
  const own = userStore.classId
  classId.value = classes.value.some(c => c.id === own) ? own : classes.value[0].id
  return true
}

const loadStudents = async () => {
  const data = await api.students.list({ class_id: classId.value, page_size: 1000 })
  unseatedStudents.value = (data?.data || []).map(s => ({
    student_id: s.id,
    student_name: s.name
  }))
}

const loadTodayChart = async () => {
  try {
    const data = await api.seating.get(classId.value)
    // 已有当天座位表：恢复行列与座位（含未排座学生）
    rowCount.value = data.row_count
    columnCount.value = data.column_count
    seatStudents.value = (data.students || []).filter(s => s.seat_row != null)
    unseatedStudents.value = (data.students || []).filter(s => s.seat_row == null)
      .map(({ student_id, student_name }) => ({ student_id, student_name }))
  } catch (e) {
    if (e?.response?.status === 404) {
      // 当天无座位表：加载学生到未排座区
      seatStudents.value = []
      await loadStudents()
    } else {
      throw e
    }
  }
}

const loadHistoryDates = async () => {
  try {
    const dates = await api.seating.getDates(classId.value)
    historyDates.value = dates || []
  } catch (e) {
    historyDates.value = []
  }
}

const initPage = async () => {
  loading.value = true
  try {
    if (!(await loadClasses())) return
    await loadTodayChart()
    await loadHistoryDates()
  } catch (e) {
    console.error('加载座位数据失败:', e)
  } finally {
    loading.value = false
  }
}

const handleClassChange = async () => {
  // 切换班级：保持用户选择的 classId 不被覆盖，仅重载该班级的学生与座位数据
  selectedHistoryDate.value = ''
  viewingHistory.value = false
  loading.value = true
  try {
    await loadTodayChart()
    await loadHistoryDates()
  } catch (e) {
    console.error('切换班级加载失败:', e)
  } finally {
    loading.value = false
  }
}

// ========== 拖拽 ==========

const handleUnseatedDragStart = (event, index) => {
  dragData.value = { from: 'unseated', index }
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', '')
}

const handleSeatDragStart = (event, r, c) => {
  if (viewingHistory.value) return
  dragData.value = { from: 'seat', row: r, col: c }
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', '')
}

const handleDragEnd = () => {
  dragData.value = null
  dragOverSeat.value = null
}

const handleDropOnSeat = (event, r, c) => {
  event.preventDefault()
  dragOverSeat.value = null
  if (viewingHistory.value || !dragData.value) return

  const source = dragData.value
  dragData.value = null

  if (source.from === 'unseated') {
    const stu = unseatedStudents.value[source.index]
    if (!stu) return
    const target = seatAt(r, c)
    if (target) {
      // 目标已有学生：目标学生回到未排座，拖动学生入座
      unseatedStudents.value.splice(source.index, 1)
      unseatedStudents.value.push(target)
    } else {
      unseatedStudents.value.splice(source.index, 1)
    }
    seatStudents.value.push({ ...stu, seat_row: r, seat_column: c })
  } else if (source.from === 'seat') {
    if (source.row === r && source.col === c) return
    const sourceStu = seatAt(source.row, source.col)
    if (!sourceStu) return
    const target = seatAt(r, c)
    if (target) {
      // 两个学生交换位置
      target.seat_row = source.row
      target.seat_column = source.col
      sourceStu.seat_row = r
      sourceStu.seat_column = c
    } else {
      sourceStu.seat_row = r
      sourceStu.seat_column = c
    }
  }
}

const handleDropOnUnseated = (event) => {
  event.preventDefault()
  if (viewingHistory.value || !dragData.value) return
  if (dragData.value.from !== 'seat') {
    dragData.value = null
    return
  }
  const { row, col } = dragData.value
  dragData.value = null
  const stu = seatAt(row, col)
  if (!stu) return
  seatStudents.value = seatStudents.value.filter(s => s !== stu)
  unseatedStudents.value.push({
    student_id: stu.student_id,
    student_name: stu.student_name
  })
}

// ========== 行列变化 ==========

const handleGridResize = () => {
  // 行列缩小时，越界座位上的学生回到未排座
  const keep = []
  const out = []
  seatStudents.value.forEach(s => {
    if (s.seat_row <= rowCount.value && s.seat_column <= columnCount.value) {
      keep.push(s)
    } else {
      out.push({ student_id: s.student_id, student_name: s.student_name })
    }
  })
  seatStudents.value = keep
  unseatedStudents.value.push(...out)
}

// ========== 随机排序 ==========

const handleRandomSeating = () => {
  const all = [
    ...seatStudents.value.map(({ student_id, student_name }) => ({ student_id, student_name })),
    ...unseatedStudents.value.map(({ student_id, student_name }) => ({ student_id, student_name }))
  ]
  if (!all.length) return

  const seatCount = rowCount.value * columnCount.value
  if (all.length > seatCount) {
    ElMessage.warning(`座位不足：学生 ${all.length} 人，座位仅 ${seatCount} 个，请先增加行数或列数`)
    return
  }

  // Fisher-Yates 洗牌，保证每个学生只出现一次且不丢失
  for (let i = all.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[all[i], all[j]] = [all[j], all[i]]
  }

  seatStudents.value = all.map((stu, idx) => ({
    ...stu,
    seat_row: Math.floor(idx / columnCount.value) + 1,
    seat_column: (idx % columnCount.value) + 1
  }))
  unseatedStudents.value = []
  ElMessage.success('随机排序完成，请检查后保存')
}

// ========== 保存 ==========

const handleSave = async () => {
  const students = [
    ...seatStudents.value,
    ...unseatedStudents.value.map(s => ({ ...s, seat_row: null, seat_column: null }))
  ]
  if (!students.length) {
    ElMessage.warning('当前没有学生可保存')
    return
  }
  try {
    await api.seating.save({
      class_id: classId.value,
      row_count: rowCount.value,
      column_count: columnCount.value,
      students
    })
    ElMessage.success('座位表保存成功')
    await loadHistoryDates()
  } catch (e) {
    console.error('保存座位表失败:', e)
  }
}

// ========== Excel 导入 ==========

const triggerImport = () => {
  if (!canImport.value) {
    ElMessage.warning('当前座位表已存在学生姓名，禁止再次导入。如需使用 Excel 名单，请先点击「清除」')
    return
  }
  fileInputRef.value?.click()
}

const handleFileChange = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  try {
    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array' })
    const sheet = wb.Sheets[wb.SheetNames[0]]
    if (!sheet) {
      ElMessage.error('Excel 文件中没有工作表')
      return
    }
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 })
    if (!rows.length) {
      ElMessage.error('Excel 文件中没有数据')
      return
    }

    // 兼容简单的一列姓名数据：取每行第一个非空单元格
    const names = []
    const seen = new Set()
    let headerSkipped = false
    for (const row of rows) {
      if (!Array.isArray(row)) continue
      const cell = row.find(c => c != null && String(c).trim() !== '')
      const name = cell ? String(cell).trim() : ''
      if (!name) continue
      // 跳过表头
      if (!headerSkipped && (name === '姓名' || name === '学生姓名' || name === '名字')) {
        headerSkipped = true
        continue
      }
      headerSkipped = true
      if (seen.has(name)) continue
      seen.add(name)
      names.push(name)
    }

    if (!names.length) {
      ElMessage.error('未从 Excel 中读取到有效的学生姓名')
      return
    }
    unseatedStudents.value = names.map(name => ({ student_id: null, student_name: name }))
    ElMessage.success(`成功导入 ${names.length} 名学生（已自动去重、去除空行）`)
  } catch (e) {
    console.error('导入 Excel 失败:', e)
    ElMessage.error('Excel 文件解析失败，请检查文件格式')
  }
}

// ========== Excel 导出 ==========

const handleExport = () => {
  const rows = displayRowCount.value
  const cols = displayColumnCount.value
  const exportData = [['', ...Array.from({ length: cols }, (_, i) => `第${i + 1}列`)]]
  for (let r = 1; r <= rows; r++) {
    const line = [`第${r}行`]
    for (let c = 1; c <= cols; c++) {
      line.push(seatAt(r, c)?.student_name || '')
    }
    exportData.push(line)
  }
  const ws = XLSX.utils.aoa_to_sheet(exportData)
  ws['!cols'] = [{ wch: 8 }, ...Array.from({ length: cols }, () => ({ wch: 10 }))]
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '座位表')
  XLSX.writeFile(wb, `座位表_${viewingHistory.value ? historyDate.value : today}.xlsx`)
  ElMessage.success('座位表导出成功')
}

// ========== 清除（仅当天） ==========

const handleClear = async () => {
  try {
    await ElMessageBox.confirm(
      `确认清除 ${today} 的座位表吗？将清空座位与未排座学生，并删除数据库中当天的座位记录。`,
      '清除座位表',
      { confirmButtonText: '确认清除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await api.seating.clear(classId.value)
    seatStudents.value = []
    unseatedStudents.value = []
    await loadHistoryDates()
    ElMessage.success('当天座位表已清除')
  } catch (e) {
    console.error('清除座位表失败:', e)
  }
}

// ========== 历史座次 ==========

const handleHistoryChange = async (date) => {
  if (!date) {
    backToToday()
    return
  }
  try {
    const data = await api.seating.get(classId.value, date)
    historyDate.value = date
    historyRowCount.value = data.row_count
    historyColumnCount.value = data.column_count
    historyStudents.value = data.students || []
    viewingHistory.value = true
  } catch (e) {
    if (e?.response?.status === 404) {
      ElMessage.warning('该日期暂无座位表数据')
    }
    selectedHistoryDate.value = ''
    viewingHistory.value = false
  }
}

const backToToday = () => {
  selectedHistoryDate.value = ''
  viewingHistory.value = false
}

onMounted(initPage)
</script>

<style scoped>
.seating-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card :deep(.el-card__body) {
  padding: 14px 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-label {
  color: #606266;
  font-size: 14px;
}

.history-alert {
  border-radius: 8px;
}

.main-area {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.unseated-card {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.unseated-list {
  height: 480px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.unseated-item {
  padding: 8px 12px;
  background: #ecf5ff;
  border: 1px dashed #a0cfff;
  border-radius: 6px;
  color: #409eff;
  font-size: 14px;
  cursor: grab;
  text-align: center;
  user-select: none;
  transition: all 0.2s;
}

.unseated-item:hover {
  background: #d9ecff;
  transform: translateY(-1px);
}

.unseated-item:active {
  cursor: grabbing;
}

.seat-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.seat-hint {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.seat-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.seat-grid {
  /* 整体展示区域大小固定：高度固定，行高列宽随行列数自动缩放 */
  height: 480px;
}

.seat-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fafafa;
  cursor: default;
  overflow: hidden;
  min-width: 0;
}

.seat-cell-filled {
  background: #e8f4ff;
  border: 1px solid #b3d8ff;
  cursor: grab;
}

.seat-cell-filled:active {
  cursor: grabbing;
}

.seat-cell.drag-over {
  border: 1px dashed #409eff;
  background: #f0f9ff;
}

.seat-pos {
  font-size: 10px;
  color: #c0c4cc;
  position: absolute;
  top: 2px;
  left: 4px;
}

.seat-name {
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 95%;
}

.seat-empty-icon {
  color: #e4e7ed;
}

.podium {
  align-self: center;
  width: 40%;
  padding: 4px 0;
  text-align: center;
  background: linear-gradient(90deg, #f5f7fa, #ecf5ff, #f5f7fa);
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #909399;
  font-size: 13px;
  letter-spacing: 4px;
}

.history-card :deep(.el-card__body) {
  padding: 12px 20px;
}

.history-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
