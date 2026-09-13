<template>
  <div class="conduct-page">
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
          <span class="filter-label">排序字段：</span>
          <el-select v-model="filterSortBy" style="width: 140px">
            <el-option label="姓名" value="name" />
            <el-option label="超行分汇总值" value="score" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">排序方式：</span>
          <el-select v-model="filterOrder" style="width: 110px">
            <el-option label="升序" value="asc" />
            <el-option label="降序" value="desc" />
          </el-select>
        </div>
        <div class="filter-spacer"></div>
        <el-button type="success" plain @click="goDetailsPage">查看全部学生明细</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table :data="summaries" v-loading="loading" stripe @row-click="handleRowClick"
        class="summary-table" :row-class-name="() => 'clickable-row'">
        <el-table-column prop="student_name" label="学生姓名" min-width="160" />
        <el-table-column label="超行分" min-width="120" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.total_score)">{{ row.total_score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default>
            <el-button type="primary" link>查看明细</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无学生数据，请先在学生管理中添加学生" />
        </template>
      </el-table>
    </el-card>

    <!-- 学生明细 Drawer -->
    <el-drawer v-model="drawerVisible" size="620px" :title="drawerTitle" destroy-on-close>
      <div class="drawer-content" v-loading="detailsLoading">
        <el-descriptions :column="3" border size="small" class="drawer-desc">
          <el-descriptions-item label="学生">{{ currentStudent?.student_name }}</el-descriptions-item>
          <el-descriptions-item label="学期">{{ currentTermName }}</el-descriptions-item>
          <el-descriptions-item label="总分">
            <span :class="scoreClass(currentStudent?.total_score)">{{ currentStudent?.total_score }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <div class="drawer-toolbar">
          <el-button type="primary" size="small" @click="openCreateDialog">新增记录</el-button>
        </div>

        <el-table :data="details" size="small" stripe>
          <el-table-column label="时间" width="110">
            <template #default="{ row }">{{ formatTime(row.record_time) }}</template>
          </el-table-column>
          <el-table-column label="分值" width="80" align="center">
            <template #default="{ row }">
              <span :class="scoreClass(row.score)">{{ row.score > 0 ? '+' + row.score : row.score }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click.stop="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click.stop="handleDeleteDetail(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无明细记录" :image-size="60" />
          </template>
        </el-table>
      </div>
    </el-drawer>

    <!-- 新增/编辑明细 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑超行分记录' : '新增超行分记录'" width="460px">
      <el-form :model="detailForm" label-width="80px" ref="detailFormRef" :rules="detailRules">
        <el-form-item label="学生">
          <el-input :model-value="currentStudent?.student_name" disabled />
        </el-form-item>
        <el-form-item label="学期">
          <el-input :model-value="currentTermName" disabled />
        </el-form-item>
        <el-form-item label="分值" prop="score">
          <el-input-number v-model="detailForm.score" :step="1" step-strictly style="width: 180px" />
        </el-form-item>
        <el-form-item label="时间" prop="record_time">
          <el-date-picker v-model="detailForm.record_time" type="datetime" placeholder="选择时间"
            value-format="YYYY-MM-DDTHH:mm:ss" style="width: 220px" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="detailForm.remark" type="textarea" :rows="2" maxlength="200" placeholder="如：上课表现良好" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveDetail">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const classes = ref([])
const terms = ref([])
const summaries = ref([])
const loading = ref(false)

const filterClassId = ref(null)
const filterTermId = ref(null)
const filterSortBy = ref('name')
const filterOrder = ref('asc')

const drawerVisible = ref(false)
const detailsLoading = ref(false)
const details = ref([])
const currentStudent = ref(null)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const saving = ref(false)
const detailFormRef = ref(null)

const detailForm = reactive({
  score: 0,
  record_time: '',
  remark: ''
})

const detailRules = {
  score: [{ required: true, message: '请输入分值', trigger: 'blur' }],
  record_time: [{ required: true, message: '请选择时间', trigger: 'change' }]
}

const currentTermName = computed(() => terms.value.find(t => t.id === filterTermId.value)?.name || '')
const drawerTitle = computed(() => `超行分明细 - ${currentStudent.value?.student_name || ''}`)

const scoreClass = (score) => score > 0 ? 'score-positive' : score < 0 ? 'score-negative' : 'score-zero'

const formatTime = (t) => t ? String(t).slice(0, 10) : ''

const loadTerms = async () => {
  const data = await api.semesters.list()
  terms.value = data || []
  // 现有接口已按 year/name 倒序返回，第一个即最新学期
  if (terms.value.length && filterTermId.value == null) {
    filterTermId.value = terms.value[0].id
  }
}

const loadClasses = async () => {
  const data = await api.classes.list()
  classes.value = data || []
  // 单班级用户默认本班；多班级用户默认第一个班级
  if (classes.value.length) {
    const own = userStore.classId
    filterClassId.value = classes.value.some(c => c.id === own) ? own : classes.value[0].id
  }
}

const loadSummary = async () => {
  if (filterTermId.value == null) {
    ElMessage.warning('请先选择学期')
    return
  }
  if (filterClassId.value == null) {
    ElMessage.warning('请先选择班级')
    return
  }
  loading.value = true
  try {
    const data = await api.conduct.getSummary({
      class_id: filterClassId.value,
      term_id: filterTermId.value,
      sort_by: filterSortBy.value,
      order: filterOrder.value
    })
    summaries.value = data || []
  } catch (e) {
    console.error('查询汇总失败:', e)
  } finally {
    loading.value = false
  }
}

const loadDetails = async (studentId) => {
  detailsLoading.value = true
  try {
    const data = await api.conduct.getDetails({
      class_id: filterClassId.value,
      term_id: filterTermId.value,
      student_id: studentId,
      order: 'desc'
    })
    details.value = data || []
  } catch (e) {
    console.error('查明细失败:', e)
  } finally {
    detailsLoading.value = false
  }
}

const handleRowClick = (row) => {
  currentStudent.value = row
  drawerVisible.value = true
  loadDetails(row.student_id)
}

const refreshCurrentStudent = async () => {
  // 明细变化后刷新当前学生汇总与明细，保证总分实时准确
  await loadSummary()
  if (currentStudent.value) {
    const fresh = summaries.value.find(s => s.student_id === currentStudent.value.student_id)
    if (fresh) currentStudent.value = fresh
    await loadDetails(currentStudent.value.student_id)
  }
}

const openCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  detailForm.score = 0
  detailForm.record_time = new Date().toISOString().slice(0, 19)
  detailForm.remark = ''
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  editingId.value = row.id
  detailForm.score = row.score
  detailForm.record_time = String(row.record_time).slice(0, 19)
  detailForm.remark = row.remark || ''
  dialogVisible.value = true
}

const handleSaveDetail = async () => {
  await detailFormRef.value?.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    if (isEdit.value) {
      await api.conduct.updateDetail(editingId.value, {
        score: detailForm.score,
        remark: detailForm.remark,
        record_time: detailForm.record_time
      })
      ElMessage.success('修改成功，汇总已同步更新')
    } else {
      await api.conduct.createDetail({
        student_id: currentStudent.value.student_id,
        term_id: filterTermId.value,
        score: detailForm.score,
        remark: detailForm.remark,
        record_time: detailForm.record_time
      })
      ElMessage.success('新增成功，汇总已同步更新')
    }
    dialogVisible.value = false
    await refreshCurrentStudent()
  } catch (e) {
    console.error('保存明细失败:', e)
  } finally {
    saving.value = false
  }
}

const handleDeleteDetail = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该条超行分记录吗？删除后汇总将同步扣减。', '删除记录',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  try {
    await api.conduct.deleteDetail(row.id)
    ElMessage.success('删除成功，汇总已同步更新')
    await refreshCurrentStudent()
  } catch (e) {
    console.error('删除明细失败:', e)
  }
}

const goDetailsPage = () => {
  const query = {}
  if (filterTermId.value != null) query.term_id = filterTermId.value
  if (filterClassId.value != null) query.class_id = filterClassId.value
  router.push({ path: '/conduct-details', query })
}

onMounted(async () => {
  await Promise.all([loadTerms(), loadClasses()])
  await loadSummary()
  inited = true
})

// 班级/学期/排序变化后自动重新查询，与换座位页行为一致
let inited = false
watch([filterClassId, filterTermId, filterSortBy, filterOrder], () => {
  if (!inited) return
  if (filterClassId.value == null || filterTermId.value == null) return
  loadSummary()
})
</script>

<style scoped>
.conduct-page {
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

.summary-table :deep(.clickable-row) {
  cursor: pointer;
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

.drawer-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.drawer-toolbar {
  display: flex;
  justify-content: flex-end;
}
</style>
