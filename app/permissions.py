from app.models import User, UserRole

def is_admin(user: User) -> bool:
    """检查是否为管理员"""
    return user.role == UserRole.ADMIN

def is_class_teacher(user: User) -> bool:
    """检查是否为班主任"""
    return user.role == UserRole.CLASS_TEACHER

def is_teacher(user: User) -> bool:
    """检查是否为任课教师"""
    return user.role == UserRole.TEACHER

def is_admin_or_class_teacher(user: User) -> bool:
    """检查是否为管理员或班主任"""
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER]

def can_manage_students(user: User) -> bool:
    """检查是否可以管理学生"""
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]

def can_manage_scores(user: User) -> bool:
    """检查是否可以管理成绩"""
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]

def can_manage_attendance(user: User) -> bool:
    """检查是否可以管理考勤"""
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]

def can_manage_classes(user: User) -> bool:
    """检查是否可以管理班级"""
    return user.role == UserRole.ADMIN

def can_manage_users(user: User) -> bool:
    """检查是否可以管理系统用户"""
    return user.role == UserRole.ADMIN

def can_view_all_data(user: User) -> bool:
    """检查是否可以查看所有数据"""
    return user.role == UserRole.ADMIN

def can_manage_teachers(user: User) -> bool:
    """检查是否可以管理教师"""
    return user.role == UserRole.ADMIN
