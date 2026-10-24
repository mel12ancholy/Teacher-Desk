<template>
  <el-dialog
    :model-value="modelValue"
    title="批量导入学生"
    width="900px"
    @update:model-value="handleVisibleChange"
    @open="resetBatchForm"
  >
    <div style="margin-bottom: 15px;">
      <el-alert title="导入说明" type="info" :closable="false">
        <ol style="margin: 10px 0 0 20px; padding: 0;">
          <li>请先<strong>下载模板</strong>获取Excel文件（推荐使用.xlsx格式）</li>
          <li>按照模板格式填写学生信息</li>
          <li>性别填写"男"或"女"，学号在班级内唯一不能重复</li>
          <li>选择班级后，上传Excel或CSV文件并点击"导入"</li>
        </ol>
      </el-alert>
      <el-alert type="success" style="margin-top: 10px;">
        <strong>推荐：</strong>使用.xlsx格式的Excel文件，无需担心编码问题！
      </el-alert>
    </div>

    <el-form :model="batchForm" label-width="80px">
      <el-form-item label="选择班级" required>
        <el-select v-model="batchForm.class_id" placeholder="请先选择班级" style="width: 100%;">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="上传文件" required>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          accept=".csv,.xlsx"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击选择文件</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">支持CSV和Excel文件（.csv, .xlsx）</div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>

    <el-divider v-if="batchForm.studentList.length > 0">
      <el-icon><Document /></el-icon> 数据预览（共 {{ batchForm.studentList.length }} 条）
    </el-divider>

    <el-table
      v-if="batchForm.studentList.length > 0"
      :data="batchForm.studentList"
      size="small"
      max-height="250"
      border
      stripe
      style="margin-top: 15px;"
    >
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="student_no" label="学号" width="100" />
      <el-table-column prop="gender" label="性别" width="80">
        <template #default="{ row }">
          <el-tag :type="row.gender === 'female' ? 'danger' : 'primary'" size="small">
            {{ row.gender === 'female' ? '女' : '男' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="电话" width="120" />
      <el-table-column prop="parent_phone" label="家长电话" width="120" />
      <el-table-column prop="address" label="地址" show-overflow-tooltip />
    </el-table>

    <template #footer>
      <el-button @click="downloadTemplate" type="info">
        <el-icon><Download /></el-icon> 下载模板
      </el-button>
      <el-button @click="resetBatchForm">重置</el-button>
      <el-button @click="handleVisibleChange(false)">取消</el-button>
      <el-button
        type="primary"
        @click="handleBatchImport"
        :loading="batchLoading"
        :disabled="!batchForm.class_id || batchForm.studentList.length === 0"
      >
        导入 {{ batchForm.studentList.length > 0 ? `(${batchForm.studentList.length}条)` : '' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Download, Document } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  classes: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'imported'])

const baseURL = '/api'

const uploadRef = ref(null)
const batchLoading = ref(false)
const batchForm = reactive({
  class_id: null,
  studentData: '',
  studentList: []
})

const handleVisibleChange = (visible) => {
  emit('update:modelValue', visible)
}

const downloadTemplate = () => {
  const data = [
    ['姓名', '学号', '性别', '电话', '家长电话', '地址'],
    ['张三', '001', '男', '13800138000', '13900139000', '北京市'],
    ['李四', '002', '女', '13800138001', '13900139001', '上海市'],
    ['王五', '003', '男', '13800138002', '13900139002', '广州市']
  ]

  const ws = XLSX.utils.aoa_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '学生信息')

  XLSX.writeFile(wb, '学生导入模板.xlsx')
}

const handleFileChange = (uploadFile) => {
  const fileName = uploadFile.name
  const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase()

  if (fileExt === '.xlsx' || fileExt === '.xls') {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result)
        const workbook = XLSX.read(data, { type: 'array' })
        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })

        if (jsonData.length > 1) {
          const header = jsonData[0].map(h => String(h).trim())

          // 校验必需表头列，避免 indexOf 匹配失败导致学号解析为空
          const missingCols = ['姓名', '学号'].filter(c => !header.includes(c))
          if (missingCols.length > 0) {
            ElMessage.error(`Excel 表头缺少必需列：${missingCols.join('、')}。请使用「下载模板」生成的文件格式`)
            batchForm.studentList = []
            batchForm.studentData = ''
            return
          }

          const rows = jsonData.slice(1).filter(row => row.some(cell => cell !== undefined && cell !== null && cell !== ''))

          batchForm.studentList = rows.map((row, idx) => {
            const getValue = (index) => row[index] !== undefined ? String(row[index]).trim() : ''

            return {
              row: idx + 2, // Excel 实际行号（第1行为表头）
              name: getValue(header.indexOf('姓名')),
              student_no: getValue(header.indexOf('学号')),
              gender: getValue(header.indexOf('性别')) === '女' ? 'female' : 'male',
              phone: getValue(header.indexOf('电话')),
              parent_phone: getValue(header.indexOf('家长电话')),
              address: getValue(header.indexOf('地址'))
            }
          })

          // 提示学号为空的行
          const emptyNoRows = batchForm.studentList.filter(s => !s.student_no)
          if (emptyNoRows.length > 0) {
            ElMessage.warning(`第 ${emptyNoRows.map(s => s.row).join('、')} 行学号为空，这些行将无法导入，请补全学号`)
          }

          const csvLines = rows.map(row => {
            return header.map((col, i) => {
              const value = row[i] !== undefined ? String(row[i]) : ''
              return value
            }).join(',')
          })
          batchForm.studentData = csvLines.join('\n')

          ElMessage.success(`Excel文件解析成功，共${batchForm.studentList.length}条数据`)
        } else {
          ElMessage.warning('Excel文件中没有数据')
        }
      } catch (err) {
        console.error('Excel解析失败:', err)
        ElMessage.error('Excel文件解析失败')
      }
    }
    reader.readAsArrayBuffer(uploadFile.raw)
  } else {
    const reader = new FileReader()
    reader.onload = (e) => {
      const arrayBuffer = e.target.result
      const uint8Array = new Uint8Array(arrayBuffer)

      let content = new TextDecoder('utf-8').decode(uint8Array)
      content = content.replace(/^\ufeff/, '')

      const chineseChars = (content.match(/[\u4e00-\u9fff]/g) || []).length

      if (chineseChars === 0) {
        try {
          const gbkContent = new TextDecoder('gbk').decode(uint8Array)
          const gbkChineseChars = (gbkContent.match(/[\u4e00-\u9fff]/g) || []).length
          if (gbkChineseChars > 0 && !gbkContent.includes('\ufffd')) {
            content = gbkContent
          }
        } catch (err) {
          // 编码检测失败，保持UTF-8
        }
      }

      const lines = content.split('\n').filter(line => line.trim())
      if (lines.length > 1) {
        lines.shift()
      }

      batchForm.studentData = lines.join('\n')
      batchForm.studentList = []

      const linesData = batchForm.studentData.split('\n').filter(line => line.trim())
      for (const line of linesData) {
        const parts = line.split(',').map(p => p.trim())
        if (parts.length < 2) continue

        const genderMap = { '男': 'male', '女': 'female' }
        batchForm.studentList.push({
          name: parts[0],
          student_no: parts[1],
          gender: genderMap[parts[2]] || 'male',
          phone: parts[3] || '',
          parent_phone: parts[4] || '',
          address: parts[5] || ''
        })
      }
    }
    reader.readAsArrayBuffer(uploadFile.raw)
  }
}

const handleBatchImport = async () => {
  if (!batchForm.class_id) {
    ElMessage.warning('请选择班级')
    return
  }

  if (!batchForm.studentList || batchForm.studentList.length === 0) {
    ElMessage.warning('请先上传文件')
    return
  }

  batchLoading.value = true

  const studentsList = batchForm.studentList.map(s => ({
    ...s,
    class_id: batchForm.class_id
  }))

  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`${baseURL}/students/batch`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: JSON.stringify({ students: studentsList })
    })

    const result = await response.json()

    if (result.success > 0) {
      ElMessage.success(`成功导入 ${result.success} 名学生`)
    }

    emit('imported', result)
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('批量导入失败')
  } finally {
    batchLoading.value = false
  }
}

const resetBatchForm = () => {
  batchForm.studentList = []
  batchForm.studentData = ''
  batchForm.class_id = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}
</script>
