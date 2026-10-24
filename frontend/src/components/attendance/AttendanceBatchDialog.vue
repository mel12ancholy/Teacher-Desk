<template>
  <el-dialog
    :model-value="modelValue"
    title="批量设置考勤"
    width="700px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="resetForm"
  >
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
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleBatchSubmit" :loading="batchLoading">
        确认批量设置
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  classes: { type: Array, default: () => [] },
  students: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const batchLoading = ref(false)
const batchStudents = ref([])

const batchForm = reactive({
  class_id: null,
  date: null,
  status: 'present',
  remark: ''
})

const resetForm = () => {
  batchForm.class_id = null
  batchForm.date = null
  batchForm.status = 'present'
  batchForm.remark = ''
  batchStudents.value = []
}

const loadBatchStudents = () => {
  if (!batchForm.class_id) {
    batchStudents.value = []
    return
  }
  batchStudents.value = props.students.filter(s => s.class_id === batchForm.class_id)
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
      emit('update:modelValue', false)
      emit('saved')
      resetForm()
    } else {
      ElMessage.error(result.errors?.[0] || '批量设置失败')
    }
  } catch (e) {
    ElMessage.error('批量设置失败')
  } finally {
    batchLoading.value = false
  }
}
</script>

<style scoped>
.student-preview {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
}

.student-tags {
  margin-top: 10px;
}
</style>
