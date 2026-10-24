from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import Homework, Class, Subject, User
from app.schemas import (
    HomeworkCreate, HomeworkUpdate, HomeworkResponse, HomeworkListResponse
)
from app.auth import get_current_active_user
from app.permissions import is_staff

router = APIRouter(prefix="/api/homeworks", tags=["作业管理"])


def get_user_class_ids(user: User) -> List[int]:
    """获取用户可以访问的班级ID列表"""
    if user.role == 'admin':
        return []
    elif user.role in ['class_teacher', 'teacher']:
        if user.class_id:
            return [user.class_id]
        return []
    elif user.role == 'student':
        if user.class_id:
            return [user.class_id]
        return []
    return []


def _due_status(h: Homework) -> str:
    """截止状态：归档 > 已截止 > 即将截止(24h内) > 进行中 > 无截止时间"""
    if h.is_archived:
        return "archived"
    if not h.due_date:
        return "no_due"
    due = h.due_date
    if due.tzinfo is not None:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    else:
        now = datetime.now()
    if due < now:
        return "overdue"
    if (due - now).total_seconds() <= 24 * 3600:
        return "due_soon"
    return "ongoing"


def _to_response(h: Homework, db: Session) -> HomeworkResponse:
    class_obj = db.query(Class).filter(Class.id == h.class_id).first()
    subject_obj = db.query(Subject).filter(Subject.id == h.subject_id).first() if h.subject_id else None
    creator = db.query(User).filter(User.id == h.created_by).first()
    return HomeworkResponse(
        id=h.id,
        title=h.title,
        content=h.content,
        class_id=h.class_id,
        subject_id=h.subject_id,
        due_date=h.due_date,
        created_by=h.created_by,
        created_at=h.created_at,
        updated_at=h.updated_at,
        class_name=class_obj.name if class_obj else None,
        subject_name=subject_obj.name if subject_obj else None,
        creator_name=creator.real_name if creator else None,
        is_archived=h.is_archived,
        due_status=_due_status(h)
    )


@router.get("", response_model=HomeworkListResponse)
def get_homeworks(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    archived: Optional[bool] = Query(None, description="按归档状态筛选：false=未归档（默认视图），true=已归档，不传=全部"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Homework)

    allowed_class_ids = get_user_class_ids(current_user)

    if current_user.role != 'admin':
        if allowed_class_ids:
            query = query.filter(Homework.class_id.in_(allowed_class_ids))
        else:
            return HomeworkListResponse(total=0, data=[])

    if class_id:
        if current_user.role != 'admin' and class_id not in allowed_class_ids:
            return HomeworkListResponse(total=0, data=[])
        query = query.filter(Homework.class_id == class_id)

    if subject_id:
        query = query.filter(Homework.subject_id == subject_id)

    if archived is not None:
        query = query.filter(Homework.is_archived == archived)

    total = query.count()
    # 未归档在前，同类内截止时间近的在前（无截止的按发布时间倒序垫底）
    homeworks = query.order_by(
        Homework.is_archived.asc(),
        Homework.due_date.asc().nullslast(),
        Homework.created_at.desc()
    ).offset((page-1)*page_size).limit(page_size).all()

    return HomeworkListResponse(total=total, data=[_to_response(h, db) for h in homeworks])


@router.put("/{homework_id}/archive", response_model=HomeworkResponse)
def archive_homework(
    homework_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """归档 / 取消归档（body: {"is_archived": true|false}），表示检查完成收尾"""
    if not is_staff(current_user):
        raise HTTPException(status_code=403, detail="只有教师可以归档作业")

    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="作业不存在")

    homework.is_archived = bool(data.get("is_archived", True))
    homework.archived_at = datetime.now() if homework.is_archived else None
    db.commit()
    db.refresh(homework)
    return _to_response(homework, db)


@router.get("/{homework_id}", response_model=HomeworkResponse)
def get_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    h = db.query(Homework).filter(Homework.id == homework_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="作业不存在")

    allowed_class_ids = get_user_class_ids(current_user)
    if current_user.role != 'admin' and h.class_id not in allowed_class_ids:
        raise HTTPException(status_code=403, detail="无权访问该作业")

    return _to_response(h, db)


@router.post("", response_model=HomeworkResponse)
def create_homework(
    data: HomeworkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not is_staff(current_user):
        raise HTTPException(status_code=403, detail="只有教师可以布置作业")

    class_obj = db.query(Class).filter(Class.id == data.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="班级不存在")

    homework = Homework(
        title=data.title,
        content=data.content,
        class_id=data.class_id,
        subject_id=data.subject_id,
        due_date=data.due_date,
        created_by=current_user.id
    )
    db.add(homework)
    db.commit()
    db.refresh(homework)

    return _to_response(homework, db)


@router.put("/{homework_id}", response_model=HomeworkResponse)
def update_homework(
    homework_id: int,
    data: HomeworkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not is_staff(current_user):
        raise HTTPException(status_code=403, detail="只有教师可以修改作业")

    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="作业不存在")

    if data.title is not None:
        homework.title = data.title
    if data.content is not None:
        homework.content = data.content
    if data.subject_id is not None:
        homework.subject_id = data.subject_id
    if data.due_date is not None:
        homework.due_date = data.due_date

    db.commit()
    db.refresh(homework)

    return _to_response(homework, db)


@router.delete("/{homework_id}")
def delete_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not is_staff(current_user):
        raise HTTPException(status_code=403, detail="只有教师可以删除作业")

    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="作业不存在")

    db.delete(homework)
    db.commit()

    return {"message": "作业已删除"}
