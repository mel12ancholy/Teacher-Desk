import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const message = error.response.data?.detail || '请求失败'
      ElMessage.error(message)
      if (error.response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    } else {
      ElMessage.error('网络错误')
    }
    return Promise.reject(error)
  }
)

export default {
  auth: {
    login: (data) => api.post('/auth/login', data),
    getCurrentUser: () => api.get('/auth/me'),
    updateProfile: (data) => api.put('/auth/profile', data)
  },
  users: {
    list: (params) => api.get('/users', { params }),
    get: (id) => api.get(`/users/${id}`),
    create: (data) => api.post('/users', data),
    update: (id, data) => api.put(`/users/${id}`, data),
    delete: (id) => api.delete(`/users/${id}`),
    resetPassword: (id) => api.put(`/users/${id}/reset-password`)
  },
  classes: {
    list: () => api.get('/classes'),
    get: (id) => api.get(`/classes/${id}`),
    create: (data) => api.post('/classes', data),
    update: (id, data) => api.put(`/classes/${id}`, data),
    delete: (id) => api.delete(`/classes/${id}`)
  },
  students: {
    list: (params) => api.get('/students', { params }),
    get: (id) => api.get(`/students/${id}`),
    create: (data) => api.post('/students', data),
    update: (id, data) => api.put(`/students/${id}`, data),
    delete: (id) => api.delete(`/students/${id}`),
    batchCreate: (data) => {
      return api.post('/students/batch', JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
      })
    }
  },
  subjects: {
    list: () => api.get('/subjects'),
    create: (data) => api.post('/subjects', data),
    update: (id, data) => api.put(`/subjects/${id}`, data),
    delete: (id) => api.delete(`/subjects/${id}`),
    getClassSubjects: (classId) => api.get(`/subjects/class/${classId}`),
    createClassSubject: (data) => api.post('/subjects/class', data),
    updateClassSubject: (id, data) => api.put(`/subjects/class/${id}`, data),
    deleteClassSubject: (id) => api.delete(`/subjects/class/${id}`),
    // 考试类型默认满分（科目 × 考试类型）
    listExamTypeFullScores: (params) => api.get('/subjects/exam-type-full-scores', { params }),
    upsertExamTypeFullScore: (data) => api.post('/subjects/exam-type-full-scores', data),
    deleteExamTypeFullScore: (id) => api.delete(`/subjects/exam-type-full-scores/${id}`)
  },
  teachers: {
    list: (params) => api.get('/teachers', { params }),
    get: (id) => api.get(`/teachers/${id}`),
    create: (data) => api.post('/teachers', data),
    update: (id, data) => api.put(`/teachers/${id}`, data),
    delete: (id) => api.delete(`/teachers/${id}`)
  },
  scores: {
    list: (params) => api.get('/scores', { params }),
    get: (id) => api.get(`/scores/${id}`),
    create: (data) => api.post('/scores', data),
    update: (id, data) => api.put(`/scores/${id}`, data),
    delete: (id) => api.delete(`/scores/${id}`),
    getStudentScores: (studentId, params) => api.get(`/scores/student/${studentId}`, { params }),
    // 年级单科平均分（人工录入参照值）
    getGradeAverages: (params) => api.get('/scores/grade-averages', { params }),
    saveGradeAverages: (data) => api.post('/scores/grade-averages', data),
    deleteGradeAverage: (id) => api.delete(`/scores/grade-averages/${id}`),
    getExamDates: (params) => api.get('/scores/exam-dates', { params }),
    // 按条件批量删除
    batchCount: (params) => api.get('/scores/batch-count', { params }),
    batchDelete: (params) => api.delete('/scores/batch-delete', { params })
  },
  semesters: {
    list: () => api.get('/semesters'),
    create: (data) => api.post('/semesters', data),
    delete: (id) => api.delete(`/semesters/${id}`)
  },
  attendance: {
    list: (params) => api.get('/attendance', { params }),
    create: (data) => api.post('/attendance', data),
    update: (id, data) => api.put(`/attendance/${id}`, data),
    delete: (id) => api.delete(`/attendance/${id}`),
    getClassStats: (classId, params) => api.get(`/attendance/statistics/class/${classId}`, { params }),
    getStudentStats: (studentId, params) => api.get(`/attendance/statistics/student/${studentId}`, { params })
  },
  dashboard: {
    getStats: (params) => api.get('/dashboard/stats', { params }),
    getClassRankings: (params) => api.get('/dashboard/rankings/classes', { params }),
    getStudentRankings: (params) => api.get('/dashboard/rankings/students', { params }),
    getSubjectRankings: (subjectId, params) => api.get(`/dashboard/rankings/subjects/${subjectId}`, { params }),
    getTrends: (params) => api.get('/dashboard/analysis/trends', { params }),
    getSubjectAnalysis: (params) => api.get('/dashboard/analysis/subjects', { params })
  },
  analytics: {
    getStudentAnalysis: (studentId, params) => api.get(`/analytics/student/${studentId}`, { params }),
    getSubjectTrend: (params) => api.get('/analytics/subject-trend', { params }),
    getClassAnalysis: (classId, params) => api.get(`/analytics/class/${classId}`, { params }),
    getComparison: (classId, params) => api.get(`/analytics/comparison`, { params: { class_id: classId, ...params } }),
    getExams: (params) => api.get('/analytics/exams', { params }),
    getExamReport: (params) => api.get('/analytics/exam-report', { params }),
    // 场次实例满分（本场某科目实际满分，优先级最高）
    setExamFullScore: (params) => api.put('/analytics/exam-full-score', null, { params }),
    clearExamFullScore: (params) => api.delete('/analytics/exam-full-score', { params })
  },
  seating: {
    get: (classId, date) => api.get('/seating', { params: { class_id: classId, ...(date ? { date } : {}) } }),
    save: (data) => api.post('/seating/save', data),
    getDates: (classId) => api.get('/seating/dates', { params: { class_id: classId } }),
    clear: (classId) => api.delete('/seating', { params: { class_id: classId } })
  },
  conduct: {
    getSummary: (params) => api.get('/conduct/summary', { params }),
    getDetails: (params) => api.get('/conduct/details', { params }),
    createDetail: (data) => api.post('/conduct/details', data),
    updateDetail: (id, data) => api.put(`/conduct/details/${id}`, data),
    deleteDetail: (id) => api.delete(`/conduct/details/${id}`)
  },
  points: {
    getRanking: (params) => api.get('/points/ranking', { params })
  },
  homeworks: {
    list: (params) => api.get('/homeworks', { params }),
    archive: (id, isArchived) => api.put(`/homeworks/${id}/archive`, { is_archived: isArchived })
  },
  pageAccess: {
    getMy: () => api.get('/page-access/my'),
    getAll: () => api.get('/page-access'),
    batchUpdate: (data) => api.put('/page-access', data)
  }
}
