"""角色权限判断 —— 全项目唯一实现，路由中不得再各自定义。

历史上多个路由文件内重复定义过 is_admin / is_teacher 等函数，且语义不一致
（有的表示"仅任课教师"，有的表示"三种角色之一"），现已统一收敛到本模块：
- is_teacher   仅任课教师
- is_staff     管理员 / 班主任 / 任课教师 三种角色之一
"""

from app.models import User, UserRole


def _role_value(user: User, role: UserRole) -> bool:
    """User.role 存字符串，做大小写容错比较，避免脏数据绕过权限判断"""
    return bool(user.role) and user.role.strip().lower() == role.value


def is_admin(user: User) -> bool:
    """检查是否为管理员"""
    return _role_value(user, UserRole.ADMIN)


def is_class_teacher(user: User) -> bool:
    """检查是否为班主任"""
    return _role_value(user, UserRole.CLASS_TEACHER)


def is_teacher(user: User) -> bool:
    """检查是否为任课教师（仅任课教师，不含管理员/班主任）"""
    return _role_value(user, UserRole.TEACHER)


def is_staff(user: User) -> bool:
    """检查是否为教职工（管理员 / 班主任 / 任课教师）"""
    return user.role is not None and user.role.strip().lower() in (
        UserRole.ADMIN.value, UserRole.CLASS_TEACHER.value, UserRole.TEACHER.value
    )


def is_admin_or_class_teacher(user: User) -> bool:
    """检查是否为管理员或班主任"""
    return is_admin(user) or is_class_teacher(user)


def can_manage_students(user: User) -> bool:
    """检查是否可以管理学生"""
    return is_staff(user)


def can_manage_scores(user: User) -> bool:
    """检查是否可以管理成绩"""
    return is_staff(user)


def can_manage_attendance(user: User) -> bool:
    """检查是否可以管理考勤"""
    return is_staff(user)


def can_manage_classes(user: User) -> bool:
    """检查是否可以管理班级"""
    return is_admin(user)


def can_manage_users(user: User) -> bool:
    """检查是否可以管理系统用户"""
    return is_admin(user)


def can_view_all_data(user: User) -> bool:
    """检查是否可以查看所有数据"""
    return is_admin(user)


def can_manage_teachers(user: User) -> bool:
    """检查是否可以管理教师"""
    return is_admin(user)
