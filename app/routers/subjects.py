from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Subject, ClassSubject, Teacher, Score, Class, UserRole
from app.schemas import (
    SubjectCreate, SubjectResponse,
    ClassSubjectCreate, ClassSubjectUpdate, ClassSubjectResponse
)
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids

router = APIRouter(prefix="/api/subjects", tags=["科目管理"])


def _to_class_subject_response(cs: ClassSubject, db: Session) -> ClassSubjectResponse:
    """组装班级科目配置响应（科目名、教师姓名、教师电话、教师在职状态）"""
    subject = db.query(Subject).filter(Subject.id == cs.subject_id).first()
    class_obj = db.query(Class).filter(Class.id == cs.class_id).first()
    teacher_name = teacher_phone = teacher_status = None
    if cs.teacher_id is not None:
        teacher = db.query(Teacher).filter(Teacher.id == cs.teacher_id).first()
        if teacher:
            teacher_name = teacher.teacher_name
            teacher_phone = teacher.phone
            teacher_status = teacher.employment_status
    return ClassSubjectResponse(
        id=cs.id,
        class_id=cs.class_id,
        class_name=class_obj.name if class_obj else None,
        subject_id=cs.subject_id,
        subject_name=subject.name if subject else None,
        teacher_id=cs.teacher_id,
        teacher_name=teacher_name,
        teacher_phone=teacher_phone,
        teacher_status=teacher_status,
        is_teaching=cs.is_teaching,
        is_score_related=cs.is_score_related,
        created_at=cs.created_at,
        updated_at=cs.updated_at
    )


def _validate_class_access(class_id: int, current_user: User, db: Session):
    """校验班级存在且当前用户有权限管理"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")
    return class_ids


# ==================== 科目底表（标准科目字典） ====================

@router.get("", response_model=List[SubjectResponse])
def get_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询科目底表（全部登录用户可查，供成绩管理等模块使用）"""
    return db.query(Subject).order_by(Subject.id).all()


@router.post("", response_model=SubjectResponse)
def create_subject(
    subject_data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """新增标准科目（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以创建科目")

    name = (subject_data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="科目名称不能为空")

    existing = db.query(Subject).filter(Subject.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="科目已存在")

    subject = Subject(name=name)
    try:
        db.add(subject)
        db.commit()
        db.refresh(subject)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建科目失败: {str(e)}")
    return subject


@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除标准科目（仅管理员）；被成绩或班级科目配置引用时禁止删除"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="只有管理员可以删除科目")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    score_count = db.query(Score).filter(Score.subject_id == subject_id).count()
    if score_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该科目已有 {score_count} 条成绩数据引用，禁止删除以保护历史数据"
        )

    cs_count = db.query(ClassSubject).filter(ClassSubject.subject_id == subject_id).count()
    if cs_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该科目已被 {cs_count} 条班级科目配置引用，请先删除相关班级科目配置"
        )

    try:
        db.delete(subject)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除科目失败: {str(e)}")
    return {"message": "科目删除成功"}


# ==================== 班级科目配置 ====================

@router.get("/class/{class_id}", response_model=List[ClassSubjectResponse])
def get_class_subjects(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询指定班级的科目配置（班级权限校验）"""
    _validate_class_access(class_id, current_user, db)
    rows = db.query(ClassSubject).filter(ClassSubject.class_id == class_id).order_by(ClassSubject.id).all()
    return [_to_class_subject_response(cs, db) for cs in rows]


@router.post("/class", response_model=ClassSubjectResponse)
def create_class_subject(
    data: ClassSubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """为班级新增科目配置（class_id + subject_id 唯一，防重复）"""
    _validate_class_access(data.class_id, current_user, db)

    subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="标准科目不存在")

    if data.teacher_id is not None:
        teacher = db.query(Teacher).filter(Teacher.id == data.teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=400, detail="任课教师不存在")
        if teacher.employment_status != "在职":
            raise HTTPException(status_code=400, detail="只能选择在职教师")

    if not data.is_teaching and data.teacher_id is not None:
        raise HTTPException(status_code=400, detail="不授课时不能选择任课教师")

    existing = db.query(ClassSubject).filter(
        ClassSubject.class_id == data.class_id,
        ClassSubject.subject_id == data.subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该班级已配置此科目，不能重复配置")

    cs = ClassSubject(
        class_id=data.class_id,
        subject_id=data.subject_id,
        teacher_id=data.teacher_id if data.is_teaching else None,
        is_teaching=data.is_teaching,
        is_score_related=data.is_score_related
    )
    try:
        db.add(cs)
        db.commit()
        db.refresh(cs)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"新增班级科目配置失败: {str(e)}")
    return _to_class_subject_response(cs, db)


@router.put("/class/{cs_id}", response_model=ClassSubjectResponse)
def update_class_subject(
    cs_id: int,
    data: ClassSubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """编辑班级科目配置（任课教师 / 是否授课 / 是否成绩相关）"""
    cs = db.query(ClassSubject).filter(ClassSubject.id == cs_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="班级科目配置不存在")
    _validate_class_access(cs.class_id, current_user, db)

    is_teaching = data.is_teaching if data.is_teaching is not None else cs.is_teaching
    teacher_id = data.teacher_id if data.teacher_id is not None else cs.teacher_id

    if data.teacher_id is not None:
        teacher = db.query(Teacher).filter(Teacher.id == data.teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=400, detail="任课教师不存在")
        if teacher.employment_status != "在职":
            raise HTTPException(status_code=400, detail="只能选择在职教师")

    # 是否授课 = 否 时强制清空任课教师
    if not is_teaching:
        teacher_id = None

    cs.teacher_id = teacher_id
    cs.is_teaching = is_teaching
    if data.is_score_related is not None:
        cs.is_score_related = data.is_score_related

    try:
        db.commit()
        db.refresh(cs)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"修改班级科目配置失败: {str(e)}")
    return _to_class_subject_response(cs, db)


@router.delete("/class/{cs_id}")
def delete_class_subject(
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除班级科目配置；已有成绩数据引用时禁止删除，建议改为「不授课/不成绩相关」"""
    cs = db.query(ClassSubject).filter(ClassSubject.id == cs_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="班级科目配置不存在")
    _validate_class_access(cs.class_id, current_user, db)

    score_count = db.query(Score).filter(
        Score.class_id == cs.class_id,
        Score.subject_id == cs.subject_id
    ).count()
    if score_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该班级该科目已有 {score_count} 条成绩数据，禁止删除；可将「是否授课/是否成绩相关」改为否"
        )

    try:
        db.delete(cs)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除班级科目配置失败: {str(e)}")
    return {"message": "班级科目配置删除成功"}
