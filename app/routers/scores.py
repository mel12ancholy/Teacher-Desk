from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models import User, Score, Student, Subject, Class, ClassSubject
from app.schemas import ScoreCreate, ScoreUpdate, ScoreResponse, ScoreListResponse
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids
from app.scoring import resolve_full_score, materialize_exam_full_scores
from app.services import LogService

router = APIRouter(prefix="/api/scores", tags=["成绩管理"])


def _check_subject_score_config(class_id: int, subject_id: int, db: Session):
    """成绩联动校验：只有班级科目配置中 is_score_related=True 的科目才能参与成绩管理"""
    cs = db.query(ClassSubject).filter(
        ClassSubject.class_id == class_id,
        ClassSubject.subject_id == subject_id
    ).first()
    if not cs:
        raise HTTPException(status_code=400, detail="该班级未配置此科目，请先在科目管理中配置")
    if not cs.is_score_related:
        raise HTTPException(status_code=400, detail="该科目未开启「是否成绩相关」，不能参与成绩管理")


def _full_score_cache(db: Session):
    """满分解析缓存：同一批查询内相同（班级,科目,考试类型,日期）只解析一次"""
    cache = {}
    def get(subject_id, exam_type, exam_date, class_id):
        from app.scoring import _exam_date_key
        key = (class_id, subject_id, exam_type, _exam_date_key(exam_date))
        if key not in cache:
            cache[key] = resolve_full_score(db, subject_id, exam_type, exam_date, class_id)
        return cache[key]
    return get

@router.get("", response_model=ScoreListResponse)
def get_scores(
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    semester: Optional[str] = None,
    exam_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    class_ids = get_accessible_class_ids(current_user, db)
    
    query = db.query(Score).filter(Score.class_id.in_(class_ids))
    
    if class_id:
        if class_id not in class_ids:
            raise HTTPException(status_code=403, detail="无权访问该班级")
        query = query.filter(Score.class_id == class_id)
    if student_id:
        query = query.filter(Score.student_id == student_id)
    if subject_id:
        query = query.filter(Score.subject_id == subject_id)
    if semester:
        query = query.filter(Score.semester == semester)
    if exam_type:
        query = query.filter(Score.exam_type == exam_type)
    
    total = query.count()
    scores = query.order_by(Score.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    full_of = _full_score_cache(db)
    for s in scores:
        student = db.query(Student).filter(Student.id == s.student_id).first()
        subject = db.query(Subject).filter(Subject.id == s.subject_id).first()
        result.append(ScoreResponse(
            id=s.id,
            student_id=s.student_id,
            subject_id=s.subject_id,
            class_id=s.class_id,
            score=s.score,
            exam_type=s.exam_type,
            exam_date=s.exam_date,
            semester=s.semester,
            created_at=s.created_at,
            student_name=student.name if student else None,
            subject_name=subject.name if subject else None,
            full_score=full_of(s.subject_id, s.exam_type, s.exam_date, s.class_id)
        ))

    return ScoreListResponse(total=total, data=result)

@router.post("", response_model=ScoreResponse)
def create_score(
    score_data: ScoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    class_ids = get_accessible_class_ids(current_user, db)
    if score_data.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权在该班级添加成绩")
    
    student = db.query(Student).filter(Student.id == score_data.student_id).first()
    if not student or student.class_id != score_data.class_id:
        raise HTTPException(status_code=400, detail="学生不存在或不在该班级")
    
    subject = db.query(Subject).filter(Subject.id == score_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=400, detail="科目不存在")

    # 成绩联动：仅 is_score_related=True 的科目可录入成绩
    _check_subject_score_config(score_data.class_id, score_data.subject_id, db)

    # 满分校验：按三层模型解析本场本科目生效满分
    full_score = resolve_full_score(
        db, score_data.subject_id, score_data.exam_type, score_data.exam_date, score_data.class_id)
    if score_data.score < 0 or score_data.score > full_score:
        raise HTTPException(status_code=400, detail=f"成绩必须在 0-{int(full_score)} 之间（本场满分 {int(full_score)}）")

    score = Score(
        student_id=score_data.student_id,
        subject_id=score_data.subject_id,
        class_id=score_data.class_id,
        score=score_data.score,
        exam_type=score_data.exam_type,
        exam_date=score_data.exam_date,
        semester=score_data.semester
    )
    db.add(score)
    db.commit()
    db.refresh(score)

    return ScoreResponse(
        id=score.id,
        student_id=score.student_id,
        subject_id=score.subject_id,
        class_id=score.class_id,
        score=score.score,
        exam_type=score.exam_type,
        exam_date=score.exam_date,
        semester=score.semester,
        created_at=score.created_at,
        student_name=student.name,
        subject_name=subject.name,
        full_score=full_score
    )

@router.put("/{score_id}", response_model=ScoreResponse)
def update_score(
    score_id: int,
    score_data: ScoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="成绩不存在")
    
    class_ids = get_accessible_class_ids(current_user, db)
    if score.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权修改该成绩")
    
    if score_data.subject_id is not None and score_data.subject_id != score.subject_id:
        # 换科目时同样要走班级科目配置校验
        _check_subject_score_config(score.class_id, score_data.subject_id, db)
        score.subject_id = score_data.subject_id
    if score_data.score is not None:
        full_score = resolve_full_score(
            db, score.subject_id, score.exam_type, score.exam_date, score.class_id)
        if score_data.score < 0 or score_data.score > full_score:
            raise HTTPException(
                status_code=400,
                detail=f"成绩必须在 0-{int(full_score)} 之间（本场满分 {int(full_score)}）")
        score.score = score_data.score
    if score_data.exam_type is not None:
        score.exam_type = score_data.exam_type
    if score_data.semester is not None:
        score.semester = score_data.semester
    if score_data.exam_date is not None:
        try:
            from datetime import date as _date
            val = score_data.exam_date
            score.exam_date = val if isinstance(val, _date) else _date.fromisoformat(str(val)[:10])
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="考试日期格式错误，应为 YYYY-MM-DD")

    db.commit()
    db.refresh(score)

    student = db.query(Student).filter(Student.id == score.student_id).first()
    subject = db.query(Subject).filter(Subject.id == score.subject_id).first()

    return ScoreResponse(
        id=score.id,
        student_id=score.student_id,
        subject_id=score.subject_id,
        class_id=score.class_id,
        score=score.score,
        exam_type=score.exam_type,
        exam_date=score.exam_date,
        semester=score.semester,
        created_at=score.created_at,
        student_name=student.name if student else None,
        subject_name=subject.name if subject else None
    )

# ==================== 按条件批量删除历史成绩 ====================

def _batch_delete_query(db: Session, current_user: User, class_id, semester, subject_id, exam_type, exam_date):
    """构造批量删除的查询（班级必选，其余条件可选）"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权操作该班级")
    query = db.query(Score).filter(Score.class_id == class_id)
    if semester:
        query = query.filter(Score.semester == semester)
    if subject_id:
        query = query.filter(Score.subject_id == subject_id)
    if exam_type:
        query = query.filter(Score.exam_type == exam_type)
    if exam_date:
        query = query.filter(Score.exam_date == _parse_exam_date(exam_date))
    return query


@router.get("/exam-dates")
def list_exam_dates(
    semester: Optional[str] = None,
    exam_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """按学期/考试类型列出已有成绩数据的考试日期（倒序），供年级均分录入选择"""
    class_ids = get_accessible_class_ids(current_user, db)
    query = db.query(Score.exam_date).filter(
        Score.class_id.in_(class_ids),
        Score.exam_date.isnot(None)
    )
    if semester:
        query = query.filter(Score.semester == semester)
    if exam_type:
        query = query.filter(Score.exam_type == exam_type)
    rows = query.distinct().order_by(Score.exam_date.desc()).all()
    return [r[0].isoformat() for r in rows if r[0]]


@router.get("/batch-count")
def batch_count_scores(
    class_id: int,
    semester: Optional[str] = None,
    subject_id: Optional[int] = None,
    exam_type: Optional[str] = None,
    exam_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """批量删除前预览命中条数"""
    total = _batch_delete_query(db, current_user, class_id, semester, subject_id, exam_type, exam_date).count()
    return {"count": total}


@router.delete("/batch-delete")
def batch_delete_scores(
    class_id: int,
    semester: Optional[str] = None,
    subject_id: Optional[int] = None,
    exam_type: Optional[str] = None,
    exam_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """按条件一键删除历史成绩（班级必选），并清理悬空的场次满分配置"""
    from app.models import ExamFullScore
    query = _batch_delete_query(db, current_user, class_id, semester, subject_id, exam_type, exam_date)
    scores = query.all()
    if not scores:
        return {"message": "没有符合条件的成绩", "deleted": 0}

    cond_desc = "/".join(filter(None, [
        semester, exam_type, exam_date,
        str(subject_id) if subject_id else None
    ]))

    try:
        # 清理受影响考试科目的场次满分物化记录（该班该场该科不再有成绩时删配置，避免悬空）
        seat_keys = {(s.subject_id, s.exam_type, s.exam_date) for s in scores}
        query.delete(synchronize_session=False)
        for subj_id, etype, edate in seat_keys:
            still = db.query(func.count(Score.id)).filter(
                Score.class_id == class_id,
                Score.subject_id == subj_id,
                Score.exam_type == etype,
                Score.exam_date == edate
            ).scalar()
            if not still:
                db.query(ExamFullScore).filter(
                    ExamFullScore.class_id == class_id,
                    ExamFullScore.subject_id == subj_id,
                    ExamFullScore.exam_type == etype,
                    ExamFullScore.exam_date == edate
                ).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")

    LogService.log_delete(
        db=db, user_id=current_user.id, username=current_user.username,
        target_type="成绩（批量删除）", target_id=class_id,
        target_name=f"班级{class_id} {cond_desc or '全部'}（{len(scores)} 条）"
    )
    return {"message": f"已删除 {len(scores)} 条成绩", "deleted": len(scores)}

@router.delete("/{score_id}")
def delete_score(
    score_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(status_code=404, detail="成绩不存在")
    
    class_ids = get_accessible_class_ids(current_user, db)
    if score.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权删除该成绩")
    
    db.delete(score)
    db.commit()
    return {"message": "成绩删除成功"}

@router.get("/student/{student_id}")
def get_student_scores(
    student_id: int,
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该学生成绩")
    
    query = db.query(Score).filter(Score.student_id == student_id)
    if semester:
        query = query.filter(Score.semester == semester)
    
    scores = query.all()
    
    result = []
    for s in scores:
        subject = db.query(Subject).filter(Subject.id == s.subject_id).first()
        result.append({
            "id": s.id,
            "subject_id": s.subject_id,
            "subject_name": subject.name if subject else None,
            "score": s.score,
            "exam_type": s.exam_type,
            "semester": s.semester
        })

    return result

from fastapi import Request
from datetime import datetime

@router.post("/batch")
async def create_scores_batch(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    import json
    import sys
    
    body = await request.body()
    body_str = body.decode('utf-8')
    
    scores_list = []
    errors_list = []
    
    try:
        body_str = body_str.replace('\x00', '').replace('\ufeff', '')
        data = json.loads(body_str)
        if isinstance(data, dict) and "scores" in data:
            scores_list = data.get("scores", [])
        elif isinstance(data, list):
            scores_list = data
        print(f"[DEBUG] 解析到成绩数据数量: {len(scores_list)}", file=sys.stderr)
    except Exception as e:
        errors_list.append(f"JSON解析错误: {str(e)}")
        print(f"[DEBUG] JSON解析错误: {str(e)}", file=sys.stderr)
    
    if not scores_list:
        return {
            "success": 0,
            "failed": 0,
            "errors": ["没有有效的成绩数据"]
        }
    
    class_ids = get_accessible_class_ids(current_user, db)
    full_of = _full_score_cache(db)
    materialize_keys = set()  # (class_id, subject_id, exam_type, exam_date)

    results = []
    errors = []
    
    for i, score_data in enumerate(scores_list):
        if not isinstance(score_data, dict):
            errors.append(f"第{i+1}行: 数据格式错误")
            continue
        
        class_id = score_data.get("class_id")
        if class_id not in class_ids:
            errors.append(f"第{i+1}行: 无权在该班级添加成绩")
            continue
        
        student_no = score_data.get("student_no")
        subject_id = score_data.get("subject_id")
        
        if not student_no:
            errors.append(f"第{i+1}行: 缺少学号")
            continue
        
        if not subject_id:
            errors.append(f"第{i+1}行: 缺少科目ID")
            continue
        
        student = db.query(Student).filter(
            Student.student_no == student_no,
            Student.class_id == class_id
        ).first()
        if not student:
            errors.append(f"第{i+1}行: 学号 {student_no} 在该班级不存在")
            continue
        
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            errors.append(f"第{i+1}行: 科目不存在")
            continue

        # 成绩联动：仅 is_score_related=True 的科目可导入成绩
        cs = db.query(ClassSubject).filter(
            ClassSubject.class_id == class_id,
            ClassSubject.subject_id == subject_id
        ).first()
        if not cs:
            errors.append(f"第{i+1}行: 该班级未配置科目「{subject.name}」，请先在科目管理中配置")
            continue
        if not cs.is_score_related:
            errors.append(f"第{i+1}行: 科目「{subject.name}」未开启「是否成绩相关」，不能导入成绩")
            continue

        score_value = score_data.get("score")
        exam_type = score_data.get("exam_type", "期中考试")
        exam_date = score_data.get("exam_date")
        try:
            score_value = float(score_value)
            # 满分按三层模型解析（场次实例 > 考试类型默认 > 科目默认 > 100）
            full_score = full_of(subject_id, exam_type, exam_date, class_id)
            if score_value < 0 or score_value > full_score:
                errors.append(f"第{i+1}行: 成绩必须在 0-{int(full_score)} 之间（{subject.name} 本场满分 {int(full_score)}）")
                continue
        except (ValueError, TypeError):
            errors.append(f"第{i+1}行: 成绩格式错误")
            continue

        score = Score(
            student_id=student.id,
            subject_id=subject_id,
            class_id=class_id,
            score=score_value,
            exam_type=exam_type,
            exam_date=exam_date,
            semester=score_data.get("semester", "")
        )
        db.add(score)
        results.append(f"{student.name}-{subject.name}")
        # 记录需要物化满分的（班级, 科目, 考试类型, 日期）
        materialize_keys.add((class_id, subject_id, exam_type, exam_date))

    # 导入成功后按班级物化本场各科满分（继承自三层解析结果，已有实例不覆盖教师手工修改）
    by_class = {}
    for cid, sid, etype, edate in materialize_keys:
        by_class.setdefault(cid, []).append((sid, etype, edate))
    for cid, items in by_class.items():
        materialize_exam_full_scores(db, cid, items)
    
    try:
        db.commit()
        print(f"[DEBUG] 批量导入成绩完成 - 成功: {len(results)}, 失败: {len(errors)}", file=sys.stderr)
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"[DEBUG] 数据库提交失败: {error_msg}", file=sys.stderr)
        errors.append(f"数据库错误: {error_msg}")
        return {
            "success": len(results),
            "failed": len(errors),
            "errors": errors
        }
    
    return {
        "success": len(results),
        "failed": len(errors),
        "errors": errors
    }


# ==================== 年级单科平均分（人工录入的年级参照值） ====================

def _parse_exam_date(value: str):
    from datetime import date as _date
    try:
        return _date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="考试日期格式错误，应为 YYYY-MM-DD")


@router.get("/grade-averages")
def get_grade_averages(
    semester: str,
    exam_type: str,
    exam_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询一场考试各科已录入的年级平均分"""
    from app.models import GradeSubjectAverage
    d = _parse_exam_date(exam_date)
    rows = db.query(GradeSubjectAverage).filter(
        GradeSubjectAverage.semester == semester,
        GradeSubjectAverage.exam_type == exam_type,
        GradeSubjectAverage.exam_date == d
    ).all()
    return [
        {"id": r.id, "subject_id": r.subject_id, "avg_score": r.avg_score} for r in rows
    ]


@router.post("/grade-averages")
def upsert_grade_averages(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """批量录入年级单科平均分（非空项 upsert，空项忽略不删除既有值）"""
    from app.models import GradeSubjectAverage, ClassSubject
    semester = (data.get("semester") or "").strip()
    exam_type = (data.get("exam_type") or "").strip()
    exam_date = data.get("exam_date")
    items = data.get("items") or []
    if not semester or not exam_type or not exam_date:
        raise HTTPException(status_code=400, detail="请提供学期、考试类型和考试日期")
    d = _parse_exam_date(exam_date)

    class_ids = get_accessible_class_ids(current_user, db)
    saved = 0
    for item in items:
        subject_id = item.get("subject_id")
        avg = item.get("avg_score")
        if not subject_id or avg is None:
            continue
        avg = float(avg)
        if avg < 0:
            raise HTTPException(status_code=400, detail="年级平均分不能为负")

        row = db.query(GradeSubjectAverage).filter(
            GradeSubjectAverage.semester == semester,
            GradeSubjectAverage.exam_type == exam_type,
            GradeSubjectAverage.exam_date == d,
            GradeSubjectAverage.subject_id == subject_id
        ).first()
        if row:
            row.avg_score = avg
        else:
            db.add(GradeSubjectAverage(
                semester=semester, exam_type=exam_type, exam_date=d,
                subject_id=subject_id, avg_score=avg
            ))
        saved += 1

    db.commit()
    LogService.log_create(
        db=db, user_id=current_user.id, username=current_user.username,
        target_type="年级均分", target_id=None,
        target_name=f"{semester} {exam_type} {exam_date}（{saved} 科）"
    )
    return {"message": f"已保存 {saved} 科年级平均分", "saved": saved}


@router.delete("/grade-averages/{avg_id}")
def delete_grade_average(
    avg_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from app.models import GradeSubjectAverage
    row = db.query(GradeSubjectAverage).filter(GradeSubjectAverage.id == avg_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除，对应科目展示回落为待录入"}




