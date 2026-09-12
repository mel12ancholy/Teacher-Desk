import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response) {
      return Promise.reject(error.response.data)
    }
    return Promise.reject(error)
  }
)

export default {
  verifyCode: (code) => api.get(`/parent/verify/${code}`),
  getStudent: (code) => api.get(`/parent/student/${code}`),
  getScores: (code, params) => api.get(`/parent/scores/${code}`, { params }),
  getNotifications: (code, params) => api.get(`/parent/notifications/${code}`, { params }),
  getHomework: (code, params) => api.get(`/parent/homework/${code}`, { params }),
  getStats: (code, params) => api.get(`/parent/stats/${code}`, { params })
}
