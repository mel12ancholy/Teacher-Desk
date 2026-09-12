<template>
  <div class="conduct-details-page">
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">学期：</span>
          <el-select v-model="filterTermId" style="width: 180px" placeholder="选择学期">
            <el-option v-for="t in terms" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">学生：</span>
          <el-select v-model="filterStudentId" style="width: 180px" placeholder="全部学生" clearable filterable>
            <el-option v-for="s in students" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">时间排序：</span>
          <el-select v-model="filterOrder" style="width: 110px">
            <el-option label="升序" value="asc" />
            <el-option label="降序" value="desc" />
          </el-select>
        </div>
        <el-button type="primary" :loading="loading" @click="loadDetails">查询</el-button>
        <div class="filter-spacer"></div>
        <el-button @click="goBack">返回汇总</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="details" v-loading="loading" stripe>
        <el-table-column prop="student_name" label="学生" min-width="120" />
        <el-table-column label="时间" min-width="120">
          <template #default="{ row }">{{ formatTime(row.record_time) }}</template>
        </el-table-column>
        <el-table-column label="分值" min-width="90" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.score)">{{ row.score > 0 ? '+' + row.score : row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="200" show-overflow-tooltip />
        <template #empty>
          <el-empty description="该学期暂无超行分明细记录" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const route = useRoute()
const router = useRouter()

const terms = ref([])
const students = ref([])
const details = ref([])
const loading = ref(false)

const filterTermId = ref(null)
const filterStudentId = ref(null)
const filterOrder = ref('desc')

const scoreClass = (score) => score > 0 ? 'score-positive' : score < 0 ? 'score-negative' : 'score-zero'
const formatTime = (t) => t ? String(t).slice(0, 10) : ''

const loadTerms = async () => {
  const data = await api.semesters.list()
  terms.value = data || []
  if (terms.value.length) {
    // 优先使用上层页面携带的学期参数
    const fromQuery = Number(route.query.term_id)
    const matched = terms.value.find(t => t.id === fromQuery)
    filterTermId.value = matched ? matched.id : terms.value[0].id
  }
}

// 学生列表与汇总接口同源：仅返回当前用户有权限管理的学生
const loadStudents = async () => {
  try {
    const data = await api.students.list({ page_size: 1000 })
    students.value = (data?.data || []).map(s => ({ id: s.id, name: s.name }))
  } catch (e) {
    students.value = []
  }
}

const loadDetails = async () => {
  if (filterTermId.value == null) {
    ElMessage.warning('请先选择学期')
    return
  }
  loading.value = true
  try {
    const params = { term_id: filterTermId.value, order: filterOrder.value }
    if (filterStudentId.value != null) {
      params.student_id = filterStudentId.value
    }
    details.value = (await api.conduct.getDetails(params)) || []
  } catch (e) {
    console.error('查询明细失败:', e)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/conduct-scores')
}

onMounted(async () => {
  await loadTerms()
  await loadStudents()
  await loadDetails()
})
</script>

<style scoped>
.conduct-details-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card :deep(.el-card__body) {
  padding: 14px 20px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #606266;
  font-size: 14px;
}

.filter-spacer {
  flex: 1;
}

.score-positive {
  color: #67c23a;
  font-weight: 600;
}

.score-negative {
  color: #f56c6c;
  font-weight: 600;
}

.score-zero {
  color: #909399;
}
</style>
