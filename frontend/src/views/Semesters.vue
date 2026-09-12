<template>
  <div class="semesters">
    <div class="page-header">
      <h1 class="page-title">学期管理</h1>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增学期
      </el-button>
    </div>

    <div class="table-container">
      <el-table :data="semesters" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="学期名称" />
        <el-table-column prop="year" label="年份" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="新增学期" width="400px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="学期名称" prop="name">
          <el-input v-model="form.name" placeholder="如: 2025-1" />
        </el-form-item>
        <el-form-item label="年份" prop="year">
          <el-input-number v-model="form.year" :min="2020" :max="2030" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/api'

const semesters = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)

const form = reactive({
  name: '',
  year: new Date().getFullYear()
})

const rules = {
  name: [{ required: true, message: '请输入学期名称', trigger: 'blur' }]
}

const loadSemesters = async () => {
  semesters.value = await api.semesters.list()
}

const handleAdd = () => {
  form.name = ''
  form.year = new Date().getFullYear()
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该学期吗?', '提示', { type: 'warning' })
    await api.semesters.delete(row.id)
    ElMessage.success('删除成功')
    loadSemesters()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  await formRef.value.validate()
  try {
    await api.semesters.create(form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    loadSemesters()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadSemesters()
})
</script>

<style scoped>
.semesters {
  padding: 20px;
}
</style>
