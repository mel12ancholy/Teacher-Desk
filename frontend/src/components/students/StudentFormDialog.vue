<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑学生' : '新增学生'"
    width="600px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="initForm"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="学号" prop="student_no">
        <el-input v-model="form.student_no" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="性别" prop="gender">
        <el-radio-group v-model="form.gender">
          <el-radio label="male">男</el-radio>
          <el-radio label="female">女</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="班级" prop="class_id">
        <el-select v-model="form.class_id" placeholder="选择班级" style="width: 100%;">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="电话" prop="phone">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="家长电话" prop="parent_phone">
        <el-input v-model="form.parent_phone" />
      </el-form-item>
      <el-form-item label="地址" prop="address">
        <el-input v-model="form.address" type="textarea" />
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
  // 编辑时传入学生行数据；新增时传 null
  student: { type: Object, default: null },
  classes: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'submit'])

const formRef = ref(null)

const form = reactive({
  name: '',
  student_no: '',
  gender: 'male',
  class_id: null,
  phone: '',
  parent_phone: '',
  address: ''
})

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }]
}

const initForm = () => {
  if (props.isEdit && props.student) {
    Object.assign(form, {
      name: props.student.name,
      student_no: props.student.student_no,
      gender: props.student.gender,
      class_id: props.student.class_id,
      phone: props.student.phone,
      parent_phone: props.student.parent_phone,
      address: props.student.address
    })
  } else {
    Object.assign(form, {
      name: '',
      student_no: '',
      gender: 'male',
      class_id: props.classes[0]?.id || null,
      phone: '',
      parent_phone: '',
      address: ''
    })
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  emit('submit', { ...form })
}
</script>
