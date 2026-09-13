// 前端页面注册表
// 用途：页面访问配置管理（/page-access）、侧边栏菜单渲染、路由可见性判断的统一数据源
// inMenu: 是否出现在侧边栏菜单；adminOnly: 仅管理员可访问（沿用原有权限规则）
export const PAGE_REGISTRY = [
  { path: '/dashboard', title: '数据仪表盘', inMenu: true, adminOnly: false },
  { path: '/classes', title: '班级管理', inMenu: true, adminOnly: true },
  { path: '/students', title: '学生管理', inMenu: true, adminOnly: false },
  { path: '/seating', title: '换座位', inMenu: true, adminOnly: false },
  { path: '/conduct-scores', title: '超行分记录', inMenu: true, adminOnly: false },
  { path: '/conduct-details', title: '超行分明细', inMenu: false, adminOnly: false },
  { path: '/scores', title: '成绩管理', inMenu: true, adminOnly: false },
  { path: '/attendance', title: '考勤管理', inMenu: true, adminOnly: false },
  { path: '/rankings', title: '班级排名', inMenu: true, adminOnly: false },
  { path: '/analysis', title: '成绩分析', inMenu: true, adminOnly: false },
  { path: '/users', title: '用户管理', inMenu: true, adminOnly: true },
  { path: '/teachers', title: '任课教师', inMenu: true, adminOnly: false },
  { path: '/subjects', title: '科目管理', inMenu: true, adminOnly: false },
  { path: '/semesters', title: '学期管理', inMenu: true, adminOnly: true },
  { path: '/logs', title: '操作日志', inMenu: true, adminOnly: true },
  { path: '/points', title: '积分系统', inMenu: true, adminOnly: false },
  { path: '/points-display', title: '积分展示', inMenu: false, adminOnly: false },
  { path: '/homework', title: '作业管理', inMenu: true, adminOnly: false },
  { path: '/notifications', title: '通知中心', inMenu: true, adminOnly: false },
  { path: '/settings', title: '系统设置', inMenu: true, adminOnly: true }
]

// 各角色显示名称
export const ROLE_LABELS = {
  admin: '管理员',
  class_teacher: '班主任',
  teacher: '任课教师'
}
