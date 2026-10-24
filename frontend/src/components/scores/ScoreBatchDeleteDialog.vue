<template>
  <el-dialog
    :model-value="modelValue"
    title="批量删除历史成绩"
    width="540px"
    @update:model-value="$emit('update:modelValue', $event)"
    @open="initForm"
  >
    <el-alert type="warning" :closable="false" style="margin-bottom: 14px;"
      title="按条件删除历史成绩（不可恢复）。班级为必选条件；条件越多删除范围越精确。删除会同时清理对应的场次满分配置。" />

    <el-form label-width="90px">
      <el-form-item label="班级" required>
        <el-select v-model="form.class_id" placeholder="选择班级（必选）" style="width: 100%;" @change="preview">
          <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="学期">
        <el-select v-model="form.semester" placeholder="不限" clearable style="width: 100%;" @change="preview">
          <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
        </el-select>
      </el-form-item>
      <el-form-item label="考试类型">
        <el-select v-model="form.exam_type" placeholder="不限" clearable filterable allow-create style="width: 100%;" @change="preview">
          <el-option v-for="t in commonExamTypes" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="考试日期">
        <el-date-picker v-model="form.exam_date" type="date" placeholder="不限" clearable
          format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%;" @change="preview" />
      </el-form-item>
      <el-form-item label="科目">
        <el-select v-model="form.subject_id" placeholder="不限" clearable style="width: 100%;" @change="preview">
          <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </el-form-item>
    </el-form>

    <div class="preview-line" v-if="form.class_id">
      <template v-if="previewCount !== null">
        当前条件将删除 <b class="danger">{{ previewCount }}</b> 条成绩记录
      </template>
      <template v-else>正在统计命中条数…</template>
    </div>

    <el-form-item label="确认输入" v-if="previewCount > 0" style="margin-top: 8px;">
      <el-input v-model="confirmText" placeholder="输入 DELETE 确认" style="width: 200px;" />
    </el-form-item>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="danger" :loading="deleting"
        :disabled="!form.class_id || !previewCount || confirmText !== 'DELETE'"
        @click="handleDelete">
        确认删除 {{ previewCount || '' }} 条
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  classes: { type: Array, default: () => [] },
  semesters: { type: Array, default: () => [] },
  subjects: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'deleted'])

const commonExamTypes = ['期中考试', '期末考试', '月考', '测验', '模拟考试']
const form = reactive({ class_id: null, semester: '', exam_type: '', exam_date: null, subject_id: null })
const previewCount = ref(null)
const confirmText = ref('')
const deleting = ref(false)

const initForm = () => {
  Object.assign(form, { class_id: null, semester: '', exam_type: '', exam_date: null, subject_id: null })
  previewCount.value = null
  confirmText.value = ''
}

let previewTimer = null
const preview = () => {
  previewCount.value = null
  confirmText.value = ''
  clearTimeout(previewTimer)
  if (!form.class_id) return
  previewTimer = setTimeout(async () => {
    try {
      const res = await api.scores.batchCount({
        class_id: form.class_id,
        semester: form.semester || undefined,
        exam_type: form.exam_type || undefined,
        exam_date: form.exam_date || undefined,
        subject_id: form.subject_id || undefined
      })
      previewCount.value = res.count
    } catch (e) {
      console.error('统计失败', e)
    }
  }, 300)
}

const handleDelete = async () => {
  deleting.value = true
  try {
    const res = await api.scores.batchDelete({
      class_id: form.class_id,
      semester: form.semester || undefined,
      exam_type: form.exam_type || undefined,
      exam_date: form.exam_date || undefined,
      subject_id: form.subject_id || undefined
    })
    ElMessage.success(res.message)
    emit('deleted')
    emit('update:modelValue', false)
  } catch (e) {
    console.error('批量删除失败', e)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.preview-line {
  background: #fef0f0;
  border-radius: 4px;
  padding: 10px 12px;
  color: #606266;
}

.danger { color: #f56c6c; font-size: 16px; }
</style>
