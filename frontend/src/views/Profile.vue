<template>
  <div class="profile">
    <div class="page-header">
      <h1 class="page-title">个人中心</h1>
    </div>

    <el-row :gutter="20">
      <!-- 基本信息（只读） -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>基本信息</template>
          <div class="info-item">
            <span class="label">用户名</span>
            <span>{{ userStore.userInfo?.username }}</span>
          </div>
          <div class="info-item">
            <span class="label">角色</span>
            <el-tag :type="getRoleTagType(userStore.userInfo?.role)" size="small">
              {{ getRoleText(userStore.userInfo?.role) }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="label">姓名</span>
            <span>{{ form.real_name }}</span>
          </div>
          <div class="info-item">
            <span class="label">电话</span>
            <span>{{ form.phone || '未填写' }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 修改资料 -->
      <el-col :span="16">
        <el-card shadow="never" class="edit-card">
          <template #header>修改个人资料</template>
          <el-form :model="form" ref="formRef" :rules="rules" label-width="80px">
            <el-form-item label="姓名" prop="real_name">
              <el-input v-model="form.real_name" placeholder="请输入姓名" />
            </el-form-item>
            <el-form-item label="电话" prop="phone">
              <el-input v-model="form.phone" placeholder="请输入联系电话" maxlength="20" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveProfile">保存资料</el-button>
            </el-form-item>
          </el-form>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="修改姓名或电话后，任课教师等页面的对应信息会自动同步"
          />
        </el-card>

        <!-- 修改密码 -->
        <el-card shadow="never" class="edit-card">
          <template #header>修改密码</template>
          <el-form :model="pwdForm" ref="pwdFormRef" :rules="pwdRules" label-width="80px">
            <el-form-item label="旧密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="不少于 6 位" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="再次输入新密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="changingPwd" @click="handleChangePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const formRef = ref(null)
const pwdFormRef = ref(null)
const saving = ref(false)
const changingPwd = ref(false)

const form = reactive({
  real_name: '',
  phone: ''
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const rules = {
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }]
}

const pwdRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const getRoleText = (role) => {
  const roleMap = {
    'admin': '管理员',
    'class_teacher': '班主任',
    'teacher': '任课教师'
  }
  return roleMap[role] || '未知角色'
}

const getRoleTagType = (role) => {
  const typeMap = {
    'admin': 'danger',
    'class_teacher': 'warning',
    'teacher': 'success'
  }
  return typeMap[role] || 'info'
}

const loadProfile = async () => {
  try {
    const me = await api.auth.getCurrentUser()
    userStore.setUserInfo(me)
    form.real_name = me.real_name || ''
    form.phone = me.phone || ''
  } catch (e) {
    console.error('获取个人信息失败', e)
  }
}

const handleSaveProfile = async () => {
  await formRef.value.validate()
  saving.value = true
  try {
    const updated = await api.auth.updateProfile({
      real_name: form.real_name,
      phone: form.phone
    })
    userStore.setUserInfo(updated)
    ElMessage.success('个人资料保存成功')
  } catch (e) {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    saving.value = false
  }
}

const handleChangePassword = async () => {
  await pwdFormRef.value.validate()
  changingPwd.value = true
  try {
    await api.auth.updateProfile({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码修改成功，下次登录请使用新密码')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    pwdFormRef.value.resetFields()
  } catch (e) {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    changingPwd.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.profile {
  padding: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  color: var(--el-text-color-secondary);
}

.edit-card {
  margin-bottom: 20px;
}
</style>
