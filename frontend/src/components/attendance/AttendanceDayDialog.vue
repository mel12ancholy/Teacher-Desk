<template>
  <el-dialog
    :model-value="modelValue"
    title="录入当日考勤"
    width="900px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="buildRows"
  >
    <el-alert :title="`${date} 的考勤记录`" type="info" :closable="false" style="margin-bottom: 15px;" />

    <div v-if="rows.length > 0">
      <el-table :data="rows" style="width: 100%" max-height="400">
        <el-table-column prop="name" label="学生姓名" width="120" />
        <el-table-column prop="student_no" label="学号" width="100" />
        <el-table-column label="考勤状态" width="200">
          <template #default="{ row }">
            <el-select v-model="row.status" style="width: 150px;">
              <el-option label="出勤" value="present" />
              <el-option label="缺勤" value="absent" />
              <el-option label="迟到" value="late" />
              <el-option label="请假" value="leave" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="备注">
          <template #default="{ row }">
            <el-input v-model="row.remark" placeholder="备注" size="small" />
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div v-else>
      <el-empty description="该班级没有学生" />
    </div>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="handleSave" :loading="saving">
        保存考勤
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // 当天日期字符串（YYYY-MM-DD）
  date: { type: String, default: '' },
  classId: { type: [Number, String], default: null },
  students: { type: Array, default: () => [] },
  attendances: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const saving = ref(false)
const rows = ref([])

const buildRows = () => {
  const dayRecords = props.attendances.filter(a => {
    const attDate = new Date(a.date).toISOString().split('T')[0]
    return attDate === props.date && a.class_id === props.classId
  })

  rows.value = props.students
    .filter(s => s.class_id === props.classId)
    .map(s => {
      const existing = dayRecords.find(a => a.student_id === s.id)
      return {
        ...s,
        status: existing?.status || 'present',
        remark: existing?.remark || '',
        hasRecord: !!existing
      }
    })
}

const handleSave = async () => {
  if (!props.classId || !props.date) {
    ElMessage.error('缺少必要参数')
    return
  }

  saving.value = true
  try {
    const token = localStorage.getItem('token')

    const attendanceList = rows.value.map(student => ({
      student_no: student.student_no,
      class_id: props.classId,
      date: props.date,
      status: student.status,
      remark: student.remark || ''
    }))

    const response = await fetch('/api/attendance/batch', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ attendances: attendanceList })
    })

    const result = await response.json()

    if (result.success > 0) {
      ElMessage.success(`考勤保存成功！${result.success} 条记录已更新`)
      emit('update:modelValue', false)
      emit('saved')
    } else if (result.errors && result.errors.length > 0) {
      ElMessage.warning(`部分保存失败: ${result.errors[0]}`)
      emit('saved')
    } else {
      ElMessage.error('保存失败')
    }
  } catch (e) {
    console.error('保存失败', e)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>
