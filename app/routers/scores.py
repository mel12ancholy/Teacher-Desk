from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models import User, Score, Student, Subject, Class
from app.schemas import ScoreCreate, ScoreUpdate, ScoreResponse, ScoreListResponse
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids

router = APIRouter(prefix="/api/scores", tags=["成绩管理"])

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
            subject_name=subject.name if subject else None
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
        subject_name=subject.name
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
    
    if score_data.score is not None:
        score.score = score_data.score
    if score_data.exam_type is not None:
        score.exam_type = score_data.exam_type
    if score_data.semester is not None:
        score.semester = score_data.semester
    
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
        semester=score.semester,
        created_at=score.created_at,
        student_name=student.name if student else None,
        subject_name=subject.name if subject else None
    )

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
        
        score_value = score_data.get("score")
        try:
            score_value = float(score_value)
            if score_value < 0 or score_value > 100:
                errors.append(f"第{i+1}行: 成绩必须在0-100之间")
                continue
        except (ValueError, TypeError):
            errors.append(f"第{i+1}行: 成绩格式错误")
            continue
        
        score = Score(
            student_id=student.id,
            subject_id=subject_id,
            class_id=class_id,
            score=score_value,
            exam_type=score_data.get("exam_type", "期中考试"),
            exam_date=score_data.get("exam_date"),
            semester=score_data.get("semester", "")
        )
        db.add(score)
        results.append(f"{student.name}-{subject.name}")
    
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
