<template>
  <div class="exam-report">
    <!-- 考试选择 + 满分设置 -->
    <div class="exam-select-row">
      <el-select v-model="selectedExamKey" placeholder="选择考试（必选）" style="width: 240px;" @change="loadReport">
        <el-option v-for="e in exams" :key="e.key" :label="e.label + `（${e.student_count}人）`" :value="e.key" />
      </el-select>
      <el-button v-if="report" size="small" @click="openFullScoreDialog">本场满分设置</el-button>
      <el-tag v-if="report?.prev_exam" type="info" effect="plain">
        进退步对照：{{ report.prev_exam.label }}
      </el-tag>
    </div>

    <template v-if="report">
      <!-- 核心指标 -->
      <el-row :gutter="12" class="metric-row">
        <el-col :span="4" v-for="m in metricCards" :key="m.label">
          <div class="metric-card">
            <div class="metric-value" :style="{ color: m.color }">{{ m.value }}</div>
            <div class="metric-label">{{ m.label }}</div>
          </div>
        </el-col>
      </el-row>

      <!-- 三率 -->
      <el-row :gutter="12" class="metric-row">
        <el-col :span="8">
          <div class="rate-card excellent">
            <div class="rate-title">优秀率（个人平均得分率 ≥90%）</div>
            <div class="rate-value">{{ report.summary.excellent_rate }}%</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="rate-card pass">
            <div class="rate-title">及格率（个人平均得分率 ≥60%）</div>
            <div class="rate-value">{{ report.summary.pass_rate }}%</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="rate-card low">
            <div class="rate-title">低分率（个人平均得分率 <40%）</div>
            <div class="rate-value">{{ report.summary.low_rate }}%</div>
          </div>
        </el-col>
      </el-row>

      <!-- 各科指标表 -->
      <el-card class="section-card" shadow="never">
        <template #header>各科成绩指标（按各自满分折算，含全校得分率对照）</template>
        <el-table :data="report.subjects" size="small" border stripe>
          <el-table-column prop="subject_name" label="科目" width="90" fixed />
          <el-table-column prop="full_score" label="满分" width="60" align="center" />
          <el-table-column prop="avg" label="平均分" width="72" />
          <el-table-column prop="grade_avg_entered" label="年级均分(录入)" width="105">
            <template #default="{ row }">
              <span v-if="row.grade_avg_entered != null" class="t-grade">{{ row.grade_avg_entered }}</span>
              <span v-else class="t-muted">待录入</span>
            </template>
          </el-table-column>
          <el-table-column prop="score_rate" label="得分率" width="72">
            <template #default="{ row }"><b>{{ row.score_rate }}%</b></template>
          </el-table-column>
          <el-table-column prop="grade_avg" label="全校得分率" width="92">
            <template #default="{ row }">
              <span :style="gradeStyle(row)">{{ row.grade_avg != null ? row.grade_avg + '%' : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="max" label="最高分" width="66" />
          <el-table-column prop="min" label="最低分" width="66" />
          <el-table-column prop="std_dev" label="标准差" width="66" />
          <el-table-column prop="excellent_rate" label="优秀率" width="72">
            <template #default="{ row }"><span class="t-excellent">{{ row.excellent_rate }}%</span></template>
          </el-table-column>
          <el-table-column prop="pass_rate" label="及格率" width="72">
            <template #default="{ row }"><span class="t-pass">{{ row.pass_rate }}%</span></template>
          </el-table-column>
          <el-table-column prop="low_rate" label="低分率" width="72">
            <template #default="{ row }"><span class="t-low">{{ row.low_rate }}%</span></template>
          </el-table-column>
          <el-table-column label="操作" width="90" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openSubjectRankDialog(row)">单科名次</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 分数段 + 科目均衡 -->
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card class="section-card" shadow="never">
            <template #header>个人平均得分率分布（10 分一段）</template>
            <div ref="segmentChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="section-card" shadow="never">
            <template #header>科目均衡（班级 vs 年级，得分率；年级线优先取录入的年级均分，未录入则按库内数据计算）</template>
            <div ref="balanceChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 临界生 -->
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card class="section-card" shadow="never">
            <template #header><span class="t-excellent">◆ 优秀临界生（平均得分率 85-89.9，距优秀线 ≤5）</span></template>
            <div v-if="report.critical.excellence.length" class="critical-list">
              <el-tag v-for="c in report.critical.excellence" :key="c.student_id" type="warning" class="critical-tag">
                {{ c.student_name }} {{ c.avg_score }}（差 {{ c.gap }}）
              </el-tag>
            </div>
            <el-empty v-else description="本场无优秀临界生" :image-size="50" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="section-card" shadow="never">
            <template #header><span class="t-low">◆ 及格临界生（平均得分率 55-59.9，距及格线 ≤5）</span></template>
            <div v-if="report.critical.pass.length" class="critical-list">
              <el-tag v-for="c in report.critical.pass" :key="c.student_id" type="danger" class="critical-tag">
                {{ c.student_name }} {{ c.avg_score }}（差 {{ c.gap }}）
              </el-tag>
            </div>
            <el-empty v-else description="本场无及格临界生" :image-size="50" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 进退步名次表 -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="rank-header">
            <span>名次与进退步（按折算总分排名；对比 {{ report.prev_exam ? report.prev_exam.label : '— 本学期首场考试，无对照 —' }}）</span>
            <el-checkbox v-if="report.prev_exam" v-model="onlyChanged">只看有变化的学生</el-checkbox>
          </div>
        </template>
        <el-table :data="visibleRankings" size="small" border stripe max-height="420">
          <el-table-column prop="rank" label="名次" width="70" sortable />
          <el-table-column prop="student_name" label="学生" width="110" />
          <el-table-column prop="total_score" label="总分" width="90" sortable>
            <template #header>总分<span class="th-sub">(原始)</span></template>
          </el-table-column>
          <el-table-column prop="norm_total" label="折算总分" width="90" sortable />
          <el-table-column prop="prev_rank" label="上次名次" width="90">
            <template #default="{ row }">{{ row.prev_rank ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="变化" width="110">
            <template #default="{ row }">
              <span v-if="row.rank_change === null" class="t-muted">—</span>
              <span v-else-if="row.rank_change > 0" class="t-up">↑ 进步 {{ row.rank_change }} 名</span>
              <span v-else-if="row.rank_change < 0" class="t-down">↓ 退步 {{ -row.rank_change }} 名</span>
              <span v-else class="t-muted">持平</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-empty v-else-if="!loading" :description="exams.length ? '请选择一场考试查看报告' : '该班级本学期暂无成绩数据'" />

    <!-- 单科名次弹窗（数据来自报告内各科明细，前端排序） -->
    <el-dialog v-model="subjectRankVisible" :title="`${subjectRankName} 单科名次 — ${report?.exam?.label || ''}`" width="440px">
      <el-table :data="subjectRankings" size="small" border stripe max-height="420">
        <el-table-column label="名次" width="70" align="center">
          <template #default="{ $index }">
            <el-tag :type="$index === 0 ? 'danger' : $index === 1 ? 'warning' : $index === 2 ? 'success' : 'info'" size="small">{{ $index + 1 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="学生" />
        <el-table-column prop="score" label="成绩" width="90" align="center">
          <template #default="{ row }">
            {{ row.score }}<span v-if="subjectRankFull && subjectRankFull !== 100" class="t-muted">/{{ subjectRankFull }}</span>
          </template>
        </el-table-column>
        <template #empty><el-empty description="该科目本场无成绩" :image-size="50" /></template>
      </el-table>
    </el-dialog>

    <!-- 本场满分设置弹窗 -->
    <el-dialog v-model="fullScoreVisible" title="本场各科满分设置" width="560px">
      <el-alert type="info" :closable="false" style="margin-bottom: 12px;"
        title="此处设置仅对本场考试生效（优先级最高），清空则回落到「考试类型默认 → 科目默认」。修改后报告立即按新满分重新折算。" />
      <el-table :data="fullScoreRows" size="small" border>
        <el-table-column prop="subject_name" label="科目" width="110" />
        <el-table-column prop="full_score" label="当前生效" width="90" align="center" />
        <el-table-column label="修改为">
          <template #default="{ row }">
            <div style="display: flex; gap: 6px; align-items: center;">
              <el-input-number v-model="row.new_score" :min="0" :max="300" :step="10" size="small" style="width: 110px;" />
              <el-button size="small" type="primary" :disabled="!row.new_score || row.new_score === row.full_score" @click="saveFullScore(row)">保存</el-button>
              <el-button size="small" :disabled="!row.instance" @click="clearFullScore(row)">还原默认</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '@/api'

const props = defineProps({
  classId: { type: [Number, String], required: true },
  semester: { type: String, required: true },
  // 从成绩管理页继承的考试类型（预选该类型最近一场考试）
  defaultExamType: { type: String, default: '' }
})

const exams = ref([])
const selectedExamKey = ref('')
const report = ref(null)
const loading = ref(false)
const onlyChanged = ref(false)

const segmentChartRef = ref()
const balanceChartRef = ref()
let segmentChart = null
let balanceChart = null

// 单科名次弹窗
const subjectRankVisible = ref(false)
const subjectRankName = ref('')
const subjectRankFull = ref(null)
const subjectRankings = ref([])

// 满分设置弹窗
const fullScoreVisible = ref(false)
const fullScoreRows = ref([])

const metricCards = computed(() => {
  const s = report.value?.summary || {}
  return [
    { label: '参考人数', value: s.student_count ?? '-' },
    { label: '平均得分率', value: (s.avg ?? '-') + '%' },
    { label: '中位数', value: (s.median ?? '-') + '%' },
    { label: '标准差', value: s.std_dev ?? '-', color: '#909399' },
    { label: '最高平均得分率', value: (s.max ?? '-') + '%', color: '#67c23a' },
    { label: '最低平均得分率', value: (s.min ?? '-') + '%', color: '#f56c6c' }
  ]
})

const visibleRankings = computed(() => {
  const list = report.value?.rankings || []
  if (!onlyChanged.value) return list
  return list.filter(r => r.rank_change !== null && r.rank_change !== 0)
})

const gradeStyle = (row) => {
  if (row.grade_avg == null || row.grade_avg === row.score_rate) return {}
  return row.score_rate >= row.grade_avg
    ? { color: '#67c23a', fontWeight: 'bold' }
    : { color: '#f56c6c', fontWeight: 'bold' }
}

const loadExams = async () => {
  selectedExamKey.value = ''
  report.value = null
  try {
    exams.value = await api.analytics.getExams({ class_id: props.classId, semester: props.semester }) || []
    if (exams.value.length) {
      // 继承考试类型：预选该类型最近一场；否则默认最近一场
      let target = exams.value[exams.value.length - 1]
      if (props.defaultExamType) {
        const matched = exams.value.filter(e => e.exam_type === props.defaultExamType)
        if (matched.length) target = matched[matched.length - 1]
      }
      selectedExamKey.value = target.key
      loadReport()
    }
  } catch (e) {
    console.error('获取考试列表失败', e)
  }
}

const loadReport = async () => {
  if (!selectedExamKey.value) return
  loading.value = true
  try {
    report.value = await api.analytics.getExamReport({
      class_id: props.classId,
      semester: props.semester,
      exam_key: selectedExamKey.value
    })
    nextTick(() => {
      initSegmentChart()
      initBalanceChart()
    })
  } catch (e) {
    console.error('获取考试报告失败', e)
  } finally {
    loading.value = false
  }
}

// ===== 单科名次（前端按报告内明细排序） =====
const openSubjectRankDialog = (subject) => {
  const name = subject.subject_name
  subjectRankName.value = name
  subjectRankFull.value = subject.full_score
  const rows = (report.value?.rankings || [])
    .map(r => ({ student_name: r.student_name, score: r.subject_scores?.[name] }))
    .filter(r => r.score != null)
  rows.sort((a, b) => b.score - a.score)
  subjectRankings.value = rows
  subjectRankVisible.value = true
}

// ===== 本场满分设置 =====
const openFullScoreDialog = () => {
  const exam = report.value?.exam
  if (!exam) return
  const [examType, dateStr] = exam.key.split('|')
  fullScoreRows.value = (report.value?.subjects || []).map(s => ({
    subject_id: s.subject_id,
    subject_name: s.subject_name,
    full_score: s.full_score,
    new_score: s.full_score,
    instance: false,
    exam_type: examType,
    exam_date: dateStr
  }))
  fullScoreVisible.value = true
}

const saveFullScore = async (row) => {
  try {
    await api.analytics.setExamFullScore({
      class_id: props.classId,
      subject_id: row.subject_id,
      exam_type: row.exam_type,
      exam_date: row.exam_date,
      full_score: row.new_score
    })
    ElMessage.success(`${row.subject_name} 本场满分已设为 ${row.new_score}`)
    fullScoreVisible.value = false
    loadReport()
  } catch (e) {
    console.error('保存满分失败', e)
  }
}

const clearFullScore = async (row) => {
  try {
    const res = await api.analytics.clearExamFullScore({
      class_id: props.classId,
      subject_id: row.subject_id,
      exam_type: row.exam_type,
      exam_date: row.exam_date
    })
    ElMessage.success(`${row.subject_name} 已还原默认（当前生效 ${res.full_score}）`)
    fullScoreVisible.value = false
    loadReport()
  } catch (e) {
    console.error('还原满分失败', e)
  }
}

const initSegmentChart = () => {
  if (!segmentChartRef.value || !report.value) return
  segmentChart?.dispose()
  segmentChart = echarts.init(segmentChartRef.value)
  const segs = report.value.segments || []
  segmentChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: segs.map(s => s.label), axisLabel: { rotate: 35 } },
    yAxis: { type: 'value', minInterval: 1, name: '人数' },
    series: [{
      type: 'bar',
      barWidth: '60%',
      data: segs.map(s => s.count),
      itemStyle: {
        color: (p) => {
          const low = parseInt(segs[p.dataIndex].label)
          return low >= 90 ? '#67c23a' : low >= 80 ? '#409eff' : low >= 60 ? '#e6a23c' : '#f56c6c'
        }
      },
      label: { show: true, position: 'top' }
    }]
  })
}

const initBalanceChart = () => {
  if (!balanceChartRef.value || !report.value) return
  balanceChart?.dispose()
  balanceChart = echarts.init(balanceChartRef.value)
  const b = report.value.balance || {}
  if (!b.subjects?.length) {
    balanceChart.setOption({
      title: { text: '暂无科目数据', left: 'center', top: 'middle', textStyle: { color: '#909399', fontSize: 14 } }
    })
    return
  }
  balanceChart.setOption({
    tooltip: {},
    legend: { bottom: 0, data: ['本班', '年级'] },
    radar: {
      indicator: b.subjects.map(s => ({ name: s, max: 100 }))
    },
    series: [{
      type: 'radar',
      data: [
        { value: b.class_avg, name: '本班', itemStyle: { color: '#409eff' }, areaStyle: { opacity: 0.2 } },
        { value: b.grade_avg, name: '年级', itemStyle: { color: '#e6a23c' }, areaStyle: { opacity: 0.1 } }
      ]
    }]
  })
}

const handleResize = () => {
  segmentChart?.resize()
  balanceChart?.resize()
}

watch(() => [props.classId, props.semester], () => {
  if (props.classId && props.semester) loadExams()
})

onMounted(() => {
  if (props.classId && props.semester) loadExams()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  segmentChart?.dispose()
  balanceChart?.dispose()
})
</script>

<style scoped>
.exam-report { padding: 4px 0; }

.exam-select-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.metric-row { margin-bottom: 12px; }

.metric-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 14px 8px;
  text-align: center;
}

.metric-value {
  font-size: 22px;
  font-weight: bold;
  color: #409eff;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.rate-card {
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}

.rate-card.excellent { background: #f0f9eb; }
.rate-card.pass { background: #ecf5ff; }
.rate-card.low { background: #fef0f0; }

.rate-title { font-size: 13px; color: #606266; }

.rate-value { font-size: 26px; font-weight: bold; margin-top: 4px; }
.rate-card.excellent .rate-value { color: #67c23a; }
.rate-card.pass .rate-value { color: #409eff; }
.rate-card.low .rate-value { color: #f56c6c; }

.section-card { margin-top: 16px; }

.th-sub { font-size: 11px; color: #909399; font-weight: normal; }

.t-excellent { color: #67c23a; }
.t-pass { color: #409eff; }
.t-low { color: #f56c6c; }
.t-grade { color: #e6a23c; font-weight: bold; }
.t-muted { color: #909399; }
.t-up { color: #67c23a; font-weight: bold; }
.t-down { color: #f56c6c; font-weight: bold; }

.critical-list { display: flex; flex-wrap: wrap; gap: 8px; }

.critical-tag { font-size: 13px; }

.rank-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
