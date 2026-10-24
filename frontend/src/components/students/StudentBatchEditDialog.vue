<template>
  <el-dialog
    :model-value="modelValue"
    title="批量修改学生"
    width="600px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="initForm"
  >
    <el-alert
      :title="`已选择 ${selectedStudents.length} 名学生`"
      type="info"
      :closable="false"
      style="margin-bottom: 20px;"
    />

    <el-form :model="batchEditForm" label-width="100px">
      <el-form-item label="修改班级">
        <el-select v-model="batchEditForm.class_id" placeholder="不修改" clearable style="width: 100%;">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="修改电话">
        <el-input v-model="batchEditForm.phone" placeholder="不修改请留空" clearable />
      </el-form-item>

      <el-form-item label="修改家长电话">
        <el-input v-model="batchEditForm.parent_phone" placeholder="不修改请留空" clearable />
      </el-form-item>

      <el-form-item label="修改地址">
        <el-input v-model="batchEditForm.address" placeholder="不修改请留空" clearable />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleBatchEdit" :loading="batchEditLoading">
        确认修改 ({{ selectedStudents.length }})
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  classes: { type: Array, default: () => [] },
  selectedStudents: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'done'])

const batchEditLoading = ref(false)

const batchEditForm = reactive({
  class_id: null,
  phone: '',
  parent_phone: '',
  address: ''
})

const initForm = () => {
  batchEditForm.class_id = null
  batchEditForm.phone = ''
  batchEditForm.parent_phone = ''
  batchEditForm.address = ''
}

const handleBatchEdit = async () => {
  if (props.selectedStudents.length === 0) {
    ElMessage.warning('请先选择要修改的学生')
    return
  }

  if (!batchEditForm.class_id && !batchEditForm.phone && !batchEditForm.parent_phone && !batchEditForm.address) {
    ElMessage.warning('请至少选择一项要修改的内容')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要修改选中的 ${props.selectedStudents.length} 名学生吗？`,
      '批量修改确认',
      {
        confirmButtonText: '确定修改',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    batchEditLoading.value = true
    let successCount = 0
    let failCount = 0
    let errorMessages = []

    for (const student of props.selectedStudents) {
      try {
        const updateData = {}
        if (batchEditForm.class_id) updateData.class_id = batchEditForm.class_id
        if (batchEditForm.phone !== '') updateData.phone = batchEditForm.phone
        if (batchEditForm.parent_phone !== '') updateData.parent_phone = batchEditForm.parent_phone
        if (batchEditForm.address !== '') updateData.address = batchEditForm.address

        if (Object.keys(updateData).length > 0) {
          await api.students.update(student.id, updateData)
          successCount++
        }
      } catch (e) {
        failCount++
        const errorMsg = e.response?.data?.detail || e.message || '未知错误'
        errorMessages.push(`${student.name}: ${errorMsg}`)
        console.error(`修改学生 ${student.name} 失败:`, errorMsg, e)
      }
    }

    batchEditLoading.value = false
    emit('done', { successCount, failCount, errorMessages })
  } catch (e) {
    if (e !== 'cancel') {
      console.error('批量修改异常:', e)
      ElMessage.error('批量修改失败')
    }
  }
}
</script>
