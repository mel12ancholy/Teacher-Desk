from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Teacher, UserRole
from app.schemas import TeacherCreate, TeacherUpdate, TeacherResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/teachers", tags=["任课教师管理"])

EMPLOYMENT_STATUSES = ("在职", "离职")


@router.get("", response_model=List[TeacherResponse])
def get_teachers(
    employment_status: Optional[str] = Query(None, description="按在职状态筛选：在职/离职"),
    keyword: Optional[str] = Query(None, description="按姓名/课程模糊搜索"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询任课教师列表（全部登录用户可查，供科目配置选择教师）"""
    query = db.query(Teacher)
    if employment_status in EMPLOYMENT_STATUSES:
        query = query.filter(Teacher.employment_status == employment_status)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(Teacher.teacher_name.like(like) | Teacher.course.like(like))
    return query.order_by(Teacher.id).all()


@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    return teacher


@router.post("", response_model=TeacherResponse)
def create_teacher(
    data: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """新增任课教师（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以新增教师")

    if data.employment_status not in EMPLOYMENT_STATUSES:
        raise HTTPException(status_code=400, detail="在职状态必须为：在职/离职")

    teacher = Teacher(
        teacher_name=data.teacher_name.strip(),
        course=(data.course or "").strip() or None,
        phone=(data.phone or "").strip() or None,
        employment_status=data.employment_status
    )
    try:
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"新增教师失败: {str(e)}")
    return teacher


@router.put("/{teacher_id}", response_model=TeacherResponse)
def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """编辑任课教师（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以修改教师")

    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    if data.employment_status is not None and data.employment_status not in EMPLOYMENT_STATUSES:
        raise HTTPException(status_code=400, detail="在职状态必须为：在职/离职")

    if data.teacher_name is not None:
        teacher.teacher_name = data.teacher_name.strip()
    if data.course is not None:
        teacher.course = data.course.strip() or None
    if data.phone is not None:
        teacher.phone = data.phone.strip() or None
    if data.employment_status is not None:
        teacher.employment_status = data.employment_status

    try:
        db.commit()
        db.refresh(teacher)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"修改教师失败: {str(e)}")
    return teacher


@router.delete("/{teacher_id}")
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除任课教师（仅管理员）；已被班级科目配置引用时禁止物理删除，建议改为离职"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以删除教师")

    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    from app.models import ClassSubject
    referenced = db.query(ClassSubject).filter(ClassSubject.teacher_id == teacher_id).count()
    if referenced > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该教师已被 {referenced} 条班级科目配置引用，请先在科目管理中取消关联，或将教师改为离职状态"
        )

    try:
        db.delete(teacher)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除教师失败: {str(e)}")
    return {"message": "教师删除成功"}
