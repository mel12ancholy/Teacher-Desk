import { ref } from 'vue'
import api from '@/api'

// 模块级缓存：同会话内成绩页、录入弹窗、批量导入弹窗共享班级科目配置
const classSubjectsCache = ref({})

/**
 * 班级科目配置（成绩联动数据源）
 * @param {import('vue').Ref<Array>} subjectsRef 全部科目列表（未指定班级时的回退，兼容旧数据展示）
 */
export function useClassSubjects(subjectsRef) {
  // 确保指定班级的科目配置已加载（带缓存）
  const ensureClassSubjects = async (classId) => {
    if (!classId) return []
    if (!classSubjectsCache.value[classId]) {
      try {
        classSubjectsCache.value[classId] = (await api.subjects.getClassSubjects(classId)) || []
      } catch (e) {
        classSubjectsCache.value[classId] = []
      }
    }
    return classSubjectsCache.value[classId]
  }

  // 指定班级的成绩相关科目（id/name）
  const scoreSubjectsFor = (classId) => {
    if (!classId) return subjectsRef.value
    const list = classSubjectsCache.value[classId] || []
    return list.filter(cs => cs.is_score_related).map(cs => ({
      id: cs.subject_id,
      name: cs.subject_name
    }))
  }

  return { classSubjectsCache, ensureClassSubjects, scoreSubjectsFor }
}
