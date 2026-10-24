<template>
  <el-dialog
    :model-value="modelValue"
    title="导入结果"
    width="700px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="result">
      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :span="6">
          <el-statistic title="总数据" :value="result.total">
            <template #prefix>
              <el-icon color="#409eff"><Document /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="成功" :value="result.success">
            <template #prefix>
              <el-icon color="#67c23a"><CircleCheck /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="失败" :value="result.failed">
            <template #prefix>
              <el-icon color="#f56c6c"><CircleClose /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="重复" :value="result.duplicate">
            <template #prefix>
              <el-icon color="#e6a23c"><Warning /></el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-progress
        :text-inside="true"
        :stroke-width="20"
        :percentage="result.total ? Math.round((result.success / result.total) * 100) : 0"
        :color="getProgressColor(result)"
        style="margin-bottom: 20px;"
      >
        <span v-if="result.failed === 0">全部导入成功！</span>
        <span v-else>成功率 {{ result.total ? Math.round((result.success / result.total) * 100) : 0 }}%</span>
      </el-progress>

      <el-alert
        v-if="result.failed > 0"
        type="warning"
        :closable="false"
        style="margin-bottom: 15px;"
      >
        <template #title>
          有 {{ result.failed }} 条数据导入失败，请查看下方失败列表
        </template>
      </el-alert>

      <el-table
        v-if="result.failed_data && result.failed_data.length > 0"
        :data="result.failed_data"
        size="small"
        max-height="300"
        border
        stripe
      >
        <el-table-column prop="row" label="行号" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="student_no" label="学号" width="120" />
        <el-table-column prop="error" label="失败原因">
          <template #default="{ row }">
            <el-tag type="danger" size="small">{{ row.error }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        v-if="result.failed_data && result.failed_data.length > 0"
        type="info"
        :closable="false"
        style="margin-top: 15px;"
      >
        <template #title>
          可点击下方"导出失败数据"按钮，修正后重新导入
        </template>
      </el-alert>
    </div>

    <template #footer>
      <el-button
        v-if="result && result.failed_data && result.failed_data.length > 0"
        type="warning"
        @click="exportFailedData"
      >
        <el-icon><Download /></el-icon> 导出失败数据
      </el-button>
      <el-button type="primary" @click="$emit('update:modelValue', false)">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { Download, Document, CircleCheck, CircleClose, Warning } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  result: { type: Object, default: null }
})

defineEmits(['update:modelValue'])

const getProgressColor = (result) => {
  const rate = result.success / result.total
  if (rate >= 0.9) return '#67c23a'
  if (rate >= 0.7) return '#e6a23c'
  return '#f56c6c'
}

const exportFailedData = () => {
  if (!props.result || !props.result.failed_data) {
    ElMessage.warning('没有失败数据')
    return
  }

  const data = [
    ['行号', '姓名', '学号', '失败原因'],
    ...props.result.failed_data.map(item => [
      item.row,
      item.name,
      item.student_no,
      item.error
    ])
  ]

  const ws = XLSX.utils.aoa_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '导入失败数据')

  XLSX.writeFile(wb, '导入失败数据.xlsx')
  ElMessage.success('失败数据已导出')
}
</script>
