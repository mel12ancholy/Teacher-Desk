<template>
  <el-dialog
    :model-value="modelValue"
    title="年级单科平均分录入"
    width="560px"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-alert type="info" :closable="false" style="margin-bottom: 12px;"
      title="录入整个年级的单科平均分作为参照（适用于联考/年级统测等本系统只有本班数据的场景）。录入后：成绩管理选科目时显示年级平均、考试报告各科表与科目均衡雷达图优先采用该参照。" />

    <el-form :inline="true">
      <el-form-item label="学期">
        <el-select v-model="semester" style="width: 120px;" @change="onConditionChange">
          <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="考试类型">
        <el-select v-model="examType" filterable allow-create style="width: 130px;" @change="onConditionChange">
          <el-option v-for="t in commonExamTypes" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
    </el-form>

    <!-- 考试日期：优先从已有成绩数据的日期中选择（学期+类型确定后加载） -->
    <div class="date-row" v-if="semester && examType">
      <template v-if="existingDates.length">
        <span class="date-label">考试日期：</span>
        <el-radio-group v-model="examDate" size="small" @change="loadExisting">
          <el-radio-button v-for="d in existingDates" :key="d" :value="d">{{ d }}</el-radio-button>
        </el-radio-group>
      </template>
      <div v-else class="date-empty">
        该学期+考试类型下暂无成绩记录
      </div>
      <el-date-picker v-model="manualDate" type="date" placeholder="或手动选择其他日期"
        format="YYYY-MM-DD" value-format="YYYY-MM-DD" size="small" style="width: 165px; margin-left: 12px;"
        @change="onManualDate" />
    </div>

    <el-table :data="rows" size="small" border stripe max-height="320" v-loading="loadingExisting">
      <el-table-column prop="subject_name" label="科目" width="110" />
      <el-table-column prop="full_score" label="默认满分" width="90" align="center" />
      <el-table-column label="年级平均分">
        <template #default="{ row }">
          <el-input-number v-model="row.avg_score" :min="0" :max="300" :step="1" size="small" style="width: 140px;" />
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="ready ? '该班级暂无成绩相关科目' : '请先选择学期、考试类型和考试日期'" :image-size="50" />
      </template>
    </el-table>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="!ready" @click="handleSave">
        保存（{{ filledCount }} 科）
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  semesters: { type: Array, default: () => [] },
  subjects: { type: Array, default: () => [] },
  // 该班级成绩相关的科目（用于表格行）
  scoreSubjects: { type: Array, default: () => [] },
  // 从成绩管理页带入的预填条件
  presetSemester: { type: String, default: '' },
  presetExamType: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const commonExamTypes = ['期中考试', '期末考试', '月考', '测验', '模拟考试']
const semester = ref('')
const examType = ref('')
const examDate = ref('')
const manualDate = ref(null)
const existingDates = ref([])
const rows = ref([])
const saving = ref(false)
const loadingExisting = ref(false)

const ready = computed(() => semester.value && examType.value && examDate.value)
const filledCount = computed(() => rows.value.filter(r => r.avg_score != null && r.avg_score !== '').length)

const buildRows = () => {
  rows.value = props.scoreSubjects.map(s => ({
    subject_id: s.subject_id || s.id,
    subject_name: s.subject_name || s.name,
    full_score: s.full_score,
    avg_score: null
  }))
}

// 学期/类型变化 → 拉取已有考试日期并默认选最近一场
const onConditionChange = async () => {
  examDate.value = ''
  manualDate.value = null
  existingDates.value = []
  buildRows()
  if (!semester.value || !examType.value) return
  try {
    existingDates.value = (await api.scores.getExamDates({
      semester: semester.value, exam_type: examType.value
    })) || []
    if (existingDates.value.length) {
      examDate.value = existingDates.value[0]
      loadExisting()
    }
  } catch (e) {
    console.error('查询考试日期失败', e)
  }
}

const onManualDate = (d) => {
  if (d) {
    examDate.value = d
    loadExisting()
  }
}

const loadExisting = async () => {
  buildRows()
  if (!ready.value) return
  loadingExisting.value = true
  try {
    const existing = await api.scores.getGradeAverages({
      semester: semester.value,
      exam_type: examType.value,
      exam_date: examDate.value
    }) || []
    const bySubject = Object.fromEntries(existing.map(e => [e.subject_id, e.avg_score]))
    rows.value.forEach(r => {
      if (bySubject[r.subject_id] != null) r.avg_score = bySubject[r.subject_id]
    })
  } catch (e) {
    console.error('查询年级均分失败', e)
  } finally {
    loadingExisting.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const res = await api.scores.saveGradeAverages({
      semester: semester.value,
      exam_type: examType.value,
      exam_date: examDate.value,
      items: rows.value
        .filter(r => r.avg_score != null && r.avg_score !== '')
        .map(r => ({ subject_id: r.subject_id, avg_score: r.avg_score }))
    })
    ElMessage.success(res.message)
    emit('saved')
    emit('update:modelValue', false)
  } catch (e) {
    console.error('保存年级均分失败', e)
  } finally {
    saving.value = false
  }
}

watch(() => props.modelValue, (visible) => {
  if (visible) {
    semester.value = props.presetSemester || props.semesters[0]?.name || ''
    examType.value = props.presetExamType || ''
    examDate.value = ''
    manualDate.value = null
    existingDates.value = []
    buildRows()
    // 已带考试类型时直接拉日期
    if (semester.value && examType.value) onConditionChange()
  }
})
</script>

<style scoped>
.date-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.date-label { font-size: 13px; color: #606266; }

.date-empty { font-size: 13px; color: #909399; }
</style>
