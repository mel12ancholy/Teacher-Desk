<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑考勤' : '录入考勤'"
    width="600px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="initForm"
  >
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
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  isEdit: { type: Boolean, default: false },
  // 编辑时传入考勤行数据；新增时传 null
  editingRow: { type: Object, default: null },
  students: { type: Array, default: () => [] },
  // 新增时的默认班级（来自页面顶部筛选）
  defaultClassId: { type: [Number, String], default: null }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const formRef = ref(null)

const form = reactive({
  student_id: null,
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

const initForm = () => {
  if (props.isEdit && props.editingRow) {
    Object.assign(form, {
      student_id: props.editingRow.student_id,
      class_id: props.editingRow.class_id,
      date: props.editingRow.date,
      status: props.editingRow.status,
      remark: props.editingRow.remark
    })
  } else {
    Object.assign(form, {
      student_id: null,
      class_id: props.defaultClassId,
      date: null,
      status: 'present',
      remark: ''
    })
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  emit('submit', { ...form })
}
</script>
