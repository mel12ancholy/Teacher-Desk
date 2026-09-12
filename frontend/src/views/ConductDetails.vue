<template>
  <div class="conduct-details-page">
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <div class="filter-item">
          <span class="filter-label">班级：</span>
          <el-select v-model="filterClassId" style="width: 160px" placeholder="选择班级">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const classes = ref([])
const terms = ref([])
const students = ref([])
const details = ref([])
const loading = ref(false)

const filterClassId = ref(null)
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

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = data || []
  if (classes.value.length) {
    // 优先使用上层页面携带的班级参数；单班级用户默认本班
    const fromQuery = Number(route.query.class_id)
    const matched = classes.value.find(c => c.id === fromQuery)
    if (matched) {
      filterClassId.value = matched.id
    } else {
      const own = userStore.classId
      filterClassId.value = classes.value.some(c => c.id === own) ? own : classes.value[0].id
    }
  }
}

// 学生列表与汇总接口同源：仅返回当前用户有权限管理的学生，并按所选班级过滤
const loadStudents = async () => {
  try {
    filterStudentId.value = null
    const params = { page_size: 1000 }
    if (filterClassId.value != null) {
      params.class_id = filterClassId.value
    }
    const data = await api.students.list(params)
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
    if (filterClassId.value != null) {
      params.class_id = filterClassId.value
    }
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
  await Promise.all([loadTerms(), loadClasses()])
  await loadStudents()
  await loadDetails()
  inited = true
})

// 筛选条件变化后自动重新查询
let inited = false
// 班级切换：重新加载该班学生选项并刷新明细
watch(filterClassId, () => {
  if (!inited) return
  loadStudents()
  loadDetails()
})
// 学期/排序/学生筛选变化：刷新明细
watch([filterTermId, filterOrder, filterStudentId], () => {
  if (!inited) return
  loadDetails()
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
