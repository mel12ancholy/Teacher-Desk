<template>
  <el-dialog
    :model-value="modelValue"
    title="批量导入成绩"
    width="800px"
    @update:model-value="handleVisibleChange"
    @open="resetBatchForm"
  >
    <div style="margin-bottom: 15px;">
      <el-alert title="导入说明" type="info" :closable="false">
        <ol style="margin: 10px 0 0 20px; padding: 0;">
          <li>请先<strong>选择班级</strong>，再<strong>下载模板</strong>（模板列由该班级「成绩相关」的科目动态生成）</li>
          <li>按模板格式填写学号和各科目成绩</li>
          <li>成绩必须在0-100之间</li>
          <li>Excel 中的等级列（如「语等」）、总分、总等、综等非成绩相关列会自动忽略</li>
          <li>选择班级、考试类型、学期后，上传文件并点击"导入"</li>
        </ol>
      </el-alert>
    </div>
    <el-form :model="batchForm" label-width="100px">
      <el-form-item label="选择班级">
        <el-select v-model="batchForm.class_id" placeholder="选择班级" style="width: 100%;" @change="handleBatchClassChange">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="考试类型">
        <el-select v-model="batchForm.exam_type" style="width: 100%;">
          <el-option label="期中考试" value="期中考试" />
          <el-option label="期末考试" value="期末考试" />
          <el-option label="月考" value="月考" />
          <el-option label="测验" value="测验" />
          <el-option label="模拟考试" value="模拟考试" />
        </el-select>
      </el-form-item>
        <el-form-item label="考试日期">
          <el-date-picker
            v-model="batchForm.exam_date"
            type="date"
            placeholder="选择考试日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>
      <el-form-item label="选择学期">
        <el-select v-model="batchForm.semester" placeholder="选择学期" style="width: 100%;">
          <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="上传文件">
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
      <el-form-item v-if="batchForm.scoreData">
        <el-input
          v-model="batchForm.scoreData"
          type="textarea"
          :rows="6"
          placeholder="预览数据"
          readonly
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="downloadTemplate">下载模板</el-button>
      <el-button @click="handleVisibleChange(false)">取消</el-button>
      <el-button type="primary" @click="handleBatchImport" :loading="batchLoading">导入</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { useClassSubjects } from '@/composables/useClassSubjects'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  classes: { type: Array, default: () => [] },
  subjects: { type: Array, default: () => [] },
  semesters: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'imported'])

const { ensureClassSubjects, scoreSubjectsFor } = useClassSubjects(
  computed(() => props.subjects)
)

const uploadRef = ref(null)
const batchLoading = ref(false)

const batchForm = reactive({
  class_id: null,
  exam_type: '期中考试',
  exam_date: null,
  semester: '',
  scoreData: '',
  scoreList: []
})

const handleVisibleChange = (visible) => {
  emit('update:modelValue', visible)
}

const resetBatchForm = () => {
  batchForm.scoreData = ''
  batchForm.scoreList = []
  batchForm.class_id = null
  batchForm.semester = ''
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 切换班级后清空已解析的文件数据（模板列随班级变化）
const handleBatchClassChange = async () => {
  batchForm.scoreData = ''
  batchForm.scoreList = []
  if (batchForm.class_id) {
    await ensureClassSubjects(batchForm.class_id)
  }
}

const handleFileChange = (uploadFile) => {
  const fileName = uploadFile.name
  const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase()

  if (fileExt === '.xlsx' || fileExt === '.xls') {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        if (!batchForm.class_id) {
          ElMessage.warning('请先选择班级再上传文件')
          return
        }
        // 确保该班级科目配置已加载（成绩相关科目为合法列）
        await ensureClassSubjects(batchForm.class_id)
        const scoreSubjects = scoreSubjectsFor(batchForm.class_id)
        if (!scoreSubjects.length) {
          ElMessage.warning('该班级没有「成绩相关」的科目，请先在科目管理中配置')
          return
        }

        const data = new Uint8Array(e.target.result)
        const workbook = XLSX.read(data, { type: 'array' })
        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })

        if (jsonData.length > 1) {
          const header = jsonData[0].map(h => String(h).trim())

          const noIndex = header.indexOf('学号')
          if (noIndex < 0) {
            ElMessage.error('模板中缺少「学号」列，请重新下载模板')
            return
          }

          // 科目列 = 表头中能匹配到该班级「成绩相关」科目的列
          // 其他列（姓名/等级列/总分/总等/综等）自动忽略
          const subjectColumns = []
          scoreSubjects.forEach(s => {
            const idx = header.indexOf(s.name)
            if (idx >= 0) subjectColumns.push({ index: idx, subject_id: s.id, name: s.name })
          })
          if (!subjectColumns.length) {
            ElMessage.error('未匹配到任何「成绩相关」科目列，请按模板填写后重新上传')
            return
          }

          const rows = jsonData.slice(1).filter(row => row.some(cell => cell !== undefined && cell !== null && cell !== ''))

          const scoreList = []
          rows.forEach(row => {
            const studentNo = row[noIndex] !== undefined ? String(row[noIndex]).trim() : ''
            if (!studentNo) return
            subjectColumns.forEach(col => {
              const cell = row[col.index]
              if (cell === undefined || cell === null || String(cell).trim() === '') return
              const score = parseFloat(cell)
              if (!isNaN(score)) {
                scoreList.push({
                  student_no: studentNo,
                  subject_id: col.subject_id,
                  subject_name: col.name,
                  score
                })
              }
            })
          })

          batchForm.scoreList = scoreList

          const csvLines = rows.map(row => {
            return header.map((col, i) => {
              const value = row[i] !== undefined ? String(row[i]) : ''
              return value
            }).join(',')
          })
          batchForm.scoreData = csvLines.join('\n')

          const subjectNames = [...new Set(subjectColumns.map(c => c.name))]
          ElMessage.success(`解析成功：${rows.length} 行，匹配科目列 [${subjectNames.join('、')}]，共 ${scoreList.length} 条成绩数据`)
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
    ElMessage.warning('请上传Excel文件（.xlsx）')
  }
}

const downloadTemplate = async () => {
  if (!batchForm.class_id) {
    ElMessage.warning('请先选择班级，模板科目列随班级科目配置生成')
    return
  }
  await ensureClassSubjects(batchForm.class_id)
  const scoreSubjects = scoreSubjectsFor(batchForm.class_id)
  if (!scoreSubjects.length) {
    ElMessage.warning('该班级没有「成绩相关」的科目，请先在科目管理中配置')
    return
  }

  // 模板列：学号 + 该班级全部成绩相关科目（总分/总等/综/等级列不属于成绩科目，不出现在模板中）
  const data = [
    ['学号', ...scoreSubjects.map(s => s.name)],
    ['1', ...scoreSubjects.map(() => '')],
    ['2', ...scoreSubjects.map(() => '')]
  ]

  const ws = XLSX.utils.aoa_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '成绩信息')

  const className = props.classes.find(c => c.id === batchForm.class_id)?.name || batchForm.class_id
  XLSX.writeFile(wb, `成绩导入模板_${className}.xlsx`)
}

const handleBatchImport = async () => {
  if (!batchForm.class_id) {
    ElMessage.warning('请选择班级')
    return
  }
  if (!batchForm.semester) {
    ElMessage.warning('请选择学期')
    return
  }
  if (!batchForm.scoreList || batchForm.scoreList.length === 0) {
    ElMessage.warning('请先上传文件')
    return
  }

  batchLoading.value = true

  const scoresList = batchForm.scoreList.map(s => ({
    student_no: s.student_no,
    class_id: batchForm.class_id,
    subject_id: s.subject_id,
    score: s.score,
    exam_type: batchForm.exam_type || '期中考试',
    exam_date: batchForm.exam_date,
    semester: batchForm.semester
  }))

  try {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/scores/batch', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: JSON.stringify({ scores: scoresList })
    })

    const result = await response.json()

    if (result.success > 0) {
      ElMessage.success(`成功导入 ${result.success} 条成绩`)
    }
    if (result.failed > 0) {
      ElMessage.warning(`导入失败 ${result.failed} 条`)
    }
    if (result.errors && result.errors.length > 0) {
      ElMessage.warning(`错误详情: ${result.errors.slice(0, 5).join(', ')}${result.errors.length > 5 ? '...' : ''}`)
    }

    emit('imported', result)
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('批量导入失败')
  } finally {
    batchLoading.value = false
  }
}
</script>
