<template>
  <div class="score-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>成绩分析</span>
          <div class="header-actions">
            <el-select v-model="selectedClass" placeholder="选择班级（必选）" style="width: 150px;" @change="onClassChange">
              <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select v-model="semester" placeholder="选择学期（必选）" style="width: 140px;" @change="onSemesterChange">
              <el-option v-for="s in semesters" :key="s.id" :label="s.name" :value="s.name" />
            </el-select>
          </div>
        </div>
      </template>

      <template v-if="selectedClass && semester">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="考试报告" name="report">
            <ExamReport :class-id="selectedClass" :semester="semester" :default-exam-type="inheritedExamType" />
          </el-tab-pane>
          <el-tab-pane label="学生分析" name="student">
            <StudentAnalysis :students="students" :semester="semester" :class-id="selectedClass" :default-subject-id="inheritedSubjectId" />
          </el-tab-pane>
        </el-tabs>
      </template>
      <el-empty v-else description="请先选择班级和学期" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import ExamReport from '@/components/analysis/ExamReport.vue'
import StudentAnalysis from '@/components/analysis/StudentAnalysis.vue'

const route = useRoute()

const classes = ref([])
const students = ref([])
const semesters = ref([])
const selectedClass = ref(null)
const semester = ref('')
const activeTab = ref('report')
// 从成绩管理页「成绩分析」按钮继承的条件
const inheritedExamType = ref('')
const inheritedSubjectId = ref(null)

const fetchClasses = async () => {
  try {
    const data = await api.classes.list()
    classes.value = data || []
  } catch (e) {
    console.error('获取班级失败', e)
  }
}

const fetchSemesters = async () => {
  try {
    const data = await api.semesters.list()
    semesters.value = data || []
    // 学期必选：默认最新学期（学期管理按 year/name 倒序返回）
    if (semesters.value.length) {
      semester.value = semesters.value[0].name
    }
  } catch (e) {
    console.error('获取学期失败', e)
  }
}

const loadStudents = async () => {
  if (!selectedClass.value) {
    students.value = []
    return
  }
  try {
    const data = await api.students.list({ class_id: selectedClass.value, page: 1, page_size: 1000 })
    students.value = data?.data || []
  } catch (e) {
    console.error('获取学生失败', e)
  }
}

const onClassChange = () => {
  loadStudents()
}

const onSemesterChange = () => {
  // 子组件通过 props watch 自动重载
}

onMounted(async () => {
  await Promise.all([fetchClasses(), fetchSemesters()])
  // 页面联动：继承成绩管理页携带的筛选条件（仅采纳合法值）
  const q = route.query || {}
  if (q.class_id) {
    const cid = Number(q.class_id)
    if (classes.value.some(c => c.id === cid)) {
      selectedClass.value = cid
    }
  }
  if (q.semester && semesters.value.some(s => s.name === q.semester)) {
    semester.value = q.semester
  }
  if (q.exam_type) {
    inheritedExamType.value = String(q.exam_type)
  }
  if (q.subject_id) {
    inheritedSubjectId.value = Number(q.subject_id)
  }
  if (selectedClass.value) {
    loadStudents()
  }
})
</script>

<style scoped>
.score-analysis { padding: 20px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.header-actions {
  display: flex;
  gap: 10px;
}
</style>
