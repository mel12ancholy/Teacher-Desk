from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Student, Semester, Class, SummaryConductScore, DetailConductScore
from app.schemas import (
    ConductSummaryResponse, ConductDetailResponse,
    ConductDetailCreate, ConductDetailUpdate
)
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids

router = APIRouter(prefix="/api/conduct", tags=["超行分记录"])


def _get_accessible_student_ids(current_user: User, db: Session) -> List[int]:
    """当前用户有权管理的学生ID列表"""
    class_ids = get_accessible_class_ids(current_user, db)
    if not class_ids:
        return []
    students = db.query(Student).filter(Student.class_id.in_(class_ids)).all()
    return [s.id for s in students]


def _check_student_access(student_id: int, current_user: User, db: Session) -> Student:
    """校验学生存在且当前用户有权限管理"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权操作该学生")
    return student


def _check_term_exists(term_id: int, db: Session) -> Semester:
    """校验学期存在"""
    semester = db.query(Semester).filter(Semester.id == term_id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="学期不存在")
    return semester


def _recompute_summary(db: Session, student_id: int, term_id: int):
    """根据明细表 SUM(score) 重算汇总，保证一致性（需在事务中调用）"""
    # SessionLocal 配置 autoflush=False，必须先 flush 让增删改对 SUM 查询可见
    db.flush()
    total = db.query(func.coalesce(func.sum(DetailConductScore.score), 0)).filter(
        DetailConductScore.student_id == student_id,
        DetailConductScore.term_id == term_id
    ).scalar()

    summary = db.query(SummaryConductScore).filter(
        SummaryConductScore.student_id == student_id,
        SummaryConductScore.term_id == term_id
    ).first()

    if summary:
        summary.total_score = total or 0
    else:
        student = db.query(Student).filter(Student.id == student_id).first()
        db.add(SummaryConductScore(
            student_id=student_id,
            student_name=student.name if student else "",
            term_id=term_id,
            total_score=total or 0
        ))


@router.get("/summary", response_model=List[ConductSummaryResponse])
def get_conduct_summary(
    term_id: int,
    sort_by: str = Query("name", pattern="^(name|score)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询学生超行分汇总（按 student + term 判断，仅补充缺失的汇总记录）"""
    _check_term_exists(term_id, db)

    class_ids = get_accessible_class_ids(current_user, db)
    students = db.query(Student).filter(Student.class_id.in_(class_ids)).all() if class_ids else []
    if not students:
        return []

    student_ids = [s.id for s in students]

    # 仅初始化不存在汇总数据的学生，不重复创建已有记录
    existing = db.query(SummaryConductScore).filter(
        SummaryConductScore.term_id == term_id,
        SummaryConductScore.student_id.in_(student_ids)
    ).all()
    existing_ids = {s.student_id for s in existing}

    for s in students:
        if s.id not in existing_ids:
            db.add(SummaryConductScore(
                student_id=s.id,
                student_name=s.name,
                term_id=term_id,
                total_score=0
            ))
    if db.new:
        db.commit()

    summaries = db.query(SummaryConductScore).filter(
        SummaryConductScore.term_id == term_id,
        SummaryConductScore.student_id.in_(student_ids)
    ).all()

    # 后端排序，避免前端大数据量处理不一致
    if sort_by == "score":
        summaries.sort(key=lambda x: x.total_score, reverse=(order == "desc"))
    else:
        summaries.sort(key=lambda x: x.student_name, reverse=(order == "desc"))

    return summaries


@router.get("/details", response_model=List[ConductDetailResponse])
def get_conduct_details(
    term_id: int,
    student_id: Optional[int] = None,
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询超行分明细（可按学生过滤），仅限当前用户管理的学生"""
    _check_term_exists(term_id, db)
    accessible_ids = _get_accessible_student_ids(current_user, db)

    query = db.query(DetailConductScore).filter(
        DetailConductScore.term_id == term_id
    )
    if not accessible_ids:
        return []
    query = query.filter(DetailConductScore.student_id.in_(accessible_ids))

    if student_id is not None:
        if student_id not in accessible_ids:
            raise HTTPException(status_code=403, detail="无权查看该学生")
        query = query.filter(DetailConductScore.student_id == student_id)

    details = query.order_by(
        DetailConductScore.record_time.desc() if order == "desc" else DetailConductScore.record_time.asc()
    ).all()
    return details


@router.post("/details", response_model=ConductDetailResponse)
def create_conduct_detail(
    data: ConductDetailCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """新增超行分明细，并在同一事务中更新汇总值"""
    student = _check_student_access(data.student_id, current_user, db)
    _check_term_exists(data.term_id, db)

    record_time = data.record_time or datetime.utcnow()
    detail = DetailConductScore(
        student_id=student.id,
        student_name=student.name,
        term_id=data.term_id,
        score=data.score,
        remark=data.remark,
        record_time=record_time,
        operator_id=current_user.id
    )
    try:
        db.add(detail)
        db.flush()
        _recompute_summary(db, student.id, data.term_id)
        db.commit()
        db.refresh(detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"新增超行分记录失败: {str(e)}")

    return detail


@router.put("/details/{detail_id}", response_model=ConductDetailResponse)
def update_conduct_detail(
    detail_id: int,
    data: ConductDetailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """修改超行分明细，并在同一事务中更新汇总值"""
    detail = db.query(DetailConductScore).filter(DetailConductScore.id == detail_id).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明细记录不存在")
    _check_student_access(detail.student_id, current_user, db)

    try:
        if data.score is not None:
            detail.score = data.score
        if data.remark is not None:
            detail.remark = data.remark
        if data.record_time is not None:
            detail.record_time = data.record_time
        _recompute_summary(db, detail.student_id, detail.term_id)
        db.commit()
        db.refresh(detail)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"修改超行分记录失败: {str(e)}")

    return detail


@router.delete("/details/{detail_id}")
def delete_conduct_detail(
    detail_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除超行分明细，并在同一事务中更新汇总值"""
    detail = db.query(DetailConductScore).filter(DetailConductScore.id == detail_id).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明细记录不存在")
    _check_student_access(detail.student_id, current_user, db)

    student_id, term_id = detail.student_id, detail.term_id
    try:
        db.delete(detail)
        _recompute_summary(db, student_id, term_id)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除超行分记录失败: {str(e)}")

    return {"message": "删除成功"}
