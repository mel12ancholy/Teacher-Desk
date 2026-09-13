import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const systemSettings = ref(JSON.parse(localStorage.getItem('system_settings') || 'null'))
  // 当前角色被隐藏的页面列表（页面访问配置，后端下发）
  const hiddenPages = ref(JSON.parse(localStorage.getItem('hidden_pages') || '[]'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')
  const isClassTeacher = computed(() => userInfo.value?.role === 'class_teacher')
  const isTeacher = computed(() => userInfo.value?.role === 'teacher')
  const classId = computed(() => userInfo.value?.class_id)

  function isPageVisible(path) {
    return !hiddenPages.value.includes(path)
  }

  async function fetchPageAccess() {
    try {
      const res = await api.pageAccess.getMy()
      hiddenPages.value = res.hidden_pages || []
      localStorage.setItem('hidden_pages', JSON.stringify(hiddenPages.value))
    } catch (e) {
      console.error('获取页面访问配置失败', e)
    }
  }

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const data = await api.auth.login(formData)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)

    const userData = await api.auth.getCurrentUser()
    userInfo.value = userData
    localStorage.setItem('user', JSON.stringify(userData))

    await fetchSystemSettings()
    await fetchPageAccess()

    return userData
  }

  async function fetchSystemSettings() {
    try {
      const res = await api.get('/settings/public')
      systemSettings.value = res.data
      localStorage.setItem('system_settings', JSON.stringify(res.data))
      document.title = res.data.system_name
    } catch (e) {
      console.error('获取系统设置失败', e)
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    systemSettings.value = null
    hiddenPages.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('system_settings')
    localStorage.removeItem('hidden_pages')
  }

  return {
    token,
    userInfo,
    systemSettings,
    hiddenPages,
    isLoggedIn,
    isAdmin,
    isClassTeacher,
    isTeacher,
    classId,
    isPageVisible,
    fetchPageAccess,
    login,
    logout,
    fetchSystemSettings
  }
})
