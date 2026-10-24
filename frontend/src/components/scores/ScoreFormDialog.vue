<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑成绩' : '录入成绩'"
    width="600px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="initForm"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="学生" prop="student_id">
        <el-select v-model="form.student_id" placeholder="选择学生" style="width: 100%;" filterable :disabled="isEdit">
          <el-option v-for="s in students" :key="s.id" :label="`${s.name} (${s.class_name})`" :value="s.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="科目" prop="subject_id">
        <el-select v-model="form.subject_id" placeholder="选择科目" style="width: 100%;" :disabled="!form.student_id">
          <el-option v-for="s in formSubjectOptions" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="成绩" prop="score">
        <el-input-number v-model="form.score" :min="0" :max="100" :step="0.5" />
      </el-form-item>
      <el-form-item label="考试类型" prop="exam_type">
        <el-select v-model="form.exam_type" style="width: 100%;" filterable allow-create placeholder="选择或输入考试类型">
          <el-option label="期中考试" value="期中考试" />
          <el-option label="期末考试" value="期末考试" />
          <el-option label="月考" value="月考" />
          <el-option label="测验" value="测验" />
          <el-option label="模拟考试" value="模拟考试" />
        </el-select>
      </el-form-item>
        <el-form-item label="考试日期" prop="exam_date">
          <el-date-picker
            v-model="form.exam_date"
            type="date"
            placeholder="选择考试日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>
      <el-form-item label="学期" prop="semester">
        <el-select v-model="form.semester" style="width: 100%;" placeholder="选择学期">
          <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { useClassSubjects } from '@/composables/useClassSubjects'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  isEdit: { type: Boolean, default: false },
  // 编辑时传入成绩行数据；新增时传 null
  editingRow: { type: Object, default: null },
  students: { type: Array, default: () => [] },
  subjects: { type: Array, default: () => [] },
  semesters: { type: Array, default: () => [] },
  classes: { type: Array, default: () => [] },
  // 新增时的默认班级（来自页面顶部筛选）
  defaultClassId: { type: [Number, String], default: null }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const formRef = ref(null)
const { ensureClassSubjects, scoreSubjectsFor } = useClassSubjects(
  computed(() => props.subjects)
)

const form = reactive({
  student_id: null,
  subject_id: null,
  class_id: null,
  score: 0,
  exam_type: '期中考试',
  exam_date: null,
  semester: ''
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  subject_id: [{ required: true, message: '请选择科目', trigger: 'change' }],
  score: [{ required: true, message: '请输入成绩', trigger: 'blur' }],
  semester: [{ required: true, message: '请选择学期', trigger: 'change' }]
}

// 科目选项：跟随所选学生的班级
const formSubjectOptions = computed(() => {
  const student = props.students.find(s => s.id === form.student_id)
  if (!student) return []
  return scoreSubjectsFor(student.class_id)
})

const initForm = async () => {
  if (props.isEdit && props.editingRow) {
    Object.assign(form, {
      student_id: props.editingRow.student_id,
      subject_id: props.editingRow.subject_id,
      class_id: props.editingRow.class_id,
      score: props.editingRow.score,
      exam_type: props.editingRow.exam_type,
      exam_date: props.editingRow.exam_date ? String(props.editingRow.exam_date).slice(0, 19) : null,
      semester: props.editingRow.semester
    })
    // 编辑时联动加载该学生班级的成绩相关科目，保证科目下拉显示名称且可选
    if (props.editingRow.class_id) {
      await ensureClassSubjects(props.editingRow.class_id)
    }
  } else {
    Object.assign(form, {
      student_id: null,
      subject_id: null,
      class_id: props.defaultClassId || props.classes[0]?.id,
      score: 0,
      exam_type: '期中考试',
      exam_date: null,
      semester: props.semesters[0]?.name || ''
    })
  }
}

// 选择学生后联动加载其班级的成绩相关科目，并清空失效的科目选择
watch(() => form.student_id, async (newId) => {
  if (props.isEdit || !newId) return
  const student = props.students.find(s => s.id === newId)
  if (student?.class_id) {
    await ensureClassSubjects(student.class_id)
    const valid = scoreSubjectsFor(student.class_id).some(s => s.id === form.subject_id)
    if (!valid) form.subject_id = null
  }
})

const handleSubmit = async () => {
  await formRef.value.validate()
  emit('submit', { ...form })
}
</script>
