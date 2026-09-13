from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from app.database import get_db
from app.models import Score, Student, Subject, Class, User
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/analytics", tags=["成绩分析"])


def _exam_sort_tuple(s: Score):
    """考试排序依据：考试日期（为空回退录入时间）+ 考试类型"""
    d = s.exam_date or s.created_at
    return (d.strftime("%Y-%m-%d") if d else "", s.exam_type or "")


def _exam_key(s: Score) -> str:
    """考试唯一标识：考试类型 + 日期（为空回退录入日期）。同一次导入的多科成绩共用一个考试。"""
    d = s.exam_date or s.created_at
    return f"{s.exam_type}|{d.strftime('%Y-%m-%d') if d else ''}"


def _exam_label(s: Score) -> str:
    d = s.exam_date or s.created_at
    date_str = d.strftime("%Y-%m-%d") if d else ""
    return f"{date_str} {s.exam_type}".strip()


@router.get("/student/{student_id}")
def get_student_analysis(
    student_id: int,
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取学生成绩分析：按「考试」维度聚合（同类型同日期的多科成绩算一次考试）"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"error": "学生不存在"}

    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该学生成绩")

    query = db.query(Score).filter(Score.student_id == student_id)
    if semester:
        query = query.filter(Score.semester == semester)

    scores = query.all()

    empty_result = {
        "student": {
            "id": student.id,
            "name": student.name,
            "class_name": student.class_obj.name if student.class_obj else None,
            "class_id": student.class_id
        },
        "summary": {
            "total_exams": 0,
            "max_score": 0,
            "max_score_subject": None,
            "min_score": 0,
            "min_score_subject": None,
            "average_score": 0
        },
        "exams": [],
        "exam_details": [],
        "rank_trend": [],
        "subject_analysis": [],
        "weak_subjects": []
    }

    if not scores:
        return empty_result

    subject_names = {}
    for s in scores:
        if s.subject_id not in subject_names:
            subj = db.query(Subject).filter(Subject.id == s.subject_id).first()
            subject_names[s.subject_id] = subj.name if subj else f"科目{s.subject_id}"

    # ---- 考试维度：排序后的考试列表 ----
    exam_map = {}
    for s in scores:
        k = _exam_key(s)
        if k not in exam_map:
            exam_map[k] = {
                "key": k,
                "exam_type": s.exam_type,
                "date": _exam_sort_tuple(s)[0],
                "label": _exam_label(s)
            }
    exams = sorted(exam_map.values(), key=lambda e: (e["date"], e["exam_type"]))

    # ---- 每次考试的各科成绩 ----
    exam_details = []
    for e in exams:
        exam_scores = [s for s in scores if _exam_key(s) == e["key"]]
        subject_scores = {
            subject_names[s.subject_id]: s.score for s in exam_scores
        }
        exam_details.append({
            "key": e["key"],
            "label": e["label"],
            "subject_scores": subject_scores,
            "total_score": round(sum(s.score for s in exam_scores), 1)
        })

    # ---- 汇总统计 ----
    valid_scores = [s for s in scores if s.score is not None]
    average_score = sum(s.score for s in valid_scores) / len(valid_scores) if valid_scores else 0
    max_s = max(valid_scores, key=lambda s: s.score)
    min_s = min(valid_scores, key=lambda s: s.score)
    summary = {
        "total_exams": len(exams),
        "max_score": max_s.score,
        "max_score_subject": subject_names.get(max_s.subject_id),
        "min_score": min_s.score,
        "min_score_subject": subject_names.get(min_s.subject_id),
        "average_score": round(average_score, 1)
    }

    # ---- 科目分析（选择学期内所有考试的平均分/最高分/最低分） ----
    subject_groups = {}
    for s in valid_scores:
        subject_groups.setdefault(s.subject_id, []).append(s.score)
    subject_analysis = [
        {
            "subject_id": sid,
            "subject_name": subject_names.get(sid),
            "avg_score": round(sum(v) / len(v), 1),
            "max_score": max(v),
            "min_score": min(v),
            "exam_count": len(v)
        }
        for sid, v in subject_groups.items()
    ]
    subject_analysis.sort(key=lambda x: x["subject_name"] or "")

    # ---- 排名趋势：每次考试按班级总分排名 ----
    class_scores_query = db.query(Score).filter(Score.class_id == student.class_id)
    if semester:
        class_scores_query = class_scores_query.filter(Score.semester == semester)
    class_scores = class_scores_query.all()

    class_exam_totals = {}  # exam_key -> {student_id: total}
    for s in class_scores:
        k = _exam_key(s)
        class_exam_totals.setdefault(k, {})
        class_exam_totals[k][s.student_id] = class_exam_totals[k].get(s.student_id, 0) + s.score

    rank_trend = []
    for e, detail in zip(exams, exam_details):
        totals = class_exam_totals.get(e["key"], {})
        my_total = totals.get(student_id)
        if my_total is None:
            continue
        rank = 1 + sum(1 for t in totals.values() if t > my_total)
        rank_trend.append({
            "key": e["key"],
            "label": e["label"],
            "total_score": round(my_total, 1),
            "rank": rank,
            "class_student_count": len(totals)
        })

    # ---- 薄弱科目：平均分低于个人总体平均分 5 分以上的科目，按差距降序 ----
    weak_subjects = []
    for sa in subject_analysis:
        gap = round(average_score - sa["avg_score"], 1)
        if gap >= 5:
            weak_subjects.append({
                "subject_id": sa["subject_id"],
                "subject_name": sa["subject_name"],
                "avg_score": sa["avg_score"],
                "gap": gap
            })
    weak_subjects.sort(key=lambda x: x["gap"], reverse=True)

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "class_name": student.class_obj.name if student.class_obj else None,
            "class_id": student.class_id
        },
        "summary": summary,
        "exams": exams,
        "exam_details": exam_details,
        "rank_trend": rank_trend,
        "subject_analysis": subject_analysis,
        "weak_subjects": weak_subjects
    }


@router.get("/subject-trend")
def get_subject_trend(
    class_id: int = Query(..., description="班级ID（单选）"),
    semesters: str = Query(..., description="学期名列表，逗号分隔（多选）"),
    subject_id: int = Query(..., description="科目ID（单选）"),
    student_ids: str = Query(..., description="学生ID列表，逗号分隔（多选）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """学生单科成绩趋势：横坐标为按时间排序的每次考试，每条折线代表一名学生"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")

    sem_list = [s.strip() for s in semesters.split(",") if s.strip()]
    stu_ids = []
    for x in student_ids.split(","):
        x = x.strip()
        if x.isdigit():
            stu_ids.append(int(x))
    if not sem_list or not stu_ids:
        return {"exams": [], "students": []}

    scores = db.query(Score).filter(
        Score.class_id == class_id,
        Score.subject_id == subject_id,
        Score.semester.in_(sem_list),
        Score.student_id.in_(stu_ids)
    ).all()

    if not scores:
        return {"exams": [], "students": []}

    multi_semester = len(set(s.semester for s in scores)) > 1

    # 考试横坐标：按（考试日期，考试类型）排序；考试日期为空回退录入时间
    exam_map = {}
    for s in scores:
        k = _exam_key(s)
        if k not in exam_map:
            label = _exam_label(s)
            if multi_semester:
                label = f"[{s.semester}] {label}"
            exam_map[k] = {"key": k, "label": label, "_sort": _exam_sort_tuple(s)}
    exams = sorted(exam_map.values(), key=lambda e: e["_sort"])
    exam_keys = [e["key"] for e in exams]

    students_map = {}
    for s in scores:
        if s.student_id not in students_map:
            student = db.query(Student).filter(Student.id == s.student_id).first()
            students_map[s.student_id] = student.name if student else f"学生{s.student_id}"

    student_series = []
    for sid, name in students_map.items():
        score_by_exam = {}
        for s in scores:
            if s.student_id == sid:
                score_by_exam[_exam_key(s)] = s.score
        student_series.append({
            "student_id": sid,
            "student_name": name,
            "scores": [score_by_exam.get(k) for k in exam_keys]
        })
    student_series.sort(key=lambda x: x["student_name"])

    return {
        "exams": [{"key": e["key"], "label": e["label"]} for e in exams],
        "students": student_series
    }


@router.get("/class/{class_id}")
def get_class_analysis(
    class_id: int,
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取班级成绩分析"""
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return {"error": "班级不存在"}

    query = db.query(Score).filter(Score.class_id == class_id)
    if semester:
        query = query.filter(Score.semester == semester)

    scores = query.all()

    if not scores:
        return {
            "class": {
                "id": class_obj.id,
                "name": class_obj.name
            },
            "summary": {
                "total_exams": 0,
                "total_students": 0,
                "average_score": 0
            },
            "subject_analysis": [],
            "score_distribution": [],
            "top_students": [],
            "weak_students": []
        }

    valid_scores = [s for s in scores if s.score]
    total_exams = len(set((s.student_id, s.subject_id) for s in valid_scores))
    total_students = len(set(s.student_id for s in valid_scores))
    average_score = sum(s.score for s in valid_scores) / len(valid_scores) if valid_scores else 0

    score_distribution = {
        "excellent": len([s for s in valid_scores if s.score >= 90]),
        "good": len([s for s in valid_scores if 80 <= s.score < 90]),
        "average": len([s for s in valid_scores if 70 <= s.score < 80]),
        "pass": len([s for s in valid_scores if 60 <= s.score < 70]),
        "fail": len([s for s in valid_scores if s.score < 60])
    }

    subject_analysis = db.query(
        Score.subject_id,
        Subject.name,
        func.avg(Score.score).label("avg_score"),
        func.count(func.distinct(Score.student_id)).label("student_count")
    ).join(
        Subject, Score.subject_id == Subject.id
    ).filter(
        Score.class_id == class_id
    )

    if semester:
        subject_analysis = subject_analysis.filter(Score.semester == semester)

    subject_stats = subject_analysis.group_by(
        Score.subject_id, Subject.name
    ).all()

    subject_analysis_list = [
        {
            "subject_id": stat.subject_id,
            "subject_name": stat.name,
            "avg_score": round(stat.avg_score, 1) if stat.avg_score else 0,
            "student_count": stat.student_count
        }
        for stat in subject_stats
    ]

    student_avgs = db.query(
        Score.student_id,
        func.avg(Score.score).label("avg_score")
    ).filter(
        Score.class_id == class_id,
        Score.score.isnot(None)
    )

    if semester:
        student_avgs = student_avgs.filter(Score.semester == semester)

    student_stats = student_avgs.group_by(Score.student_id).all()

    student_list = []
    for stat in student_stats:
        student = db.query(Student).filter(Student.id == stat.student_id).first()
        if student:
            student_list.append({
                "student_id": stat.student_id,
                "student_name": student.name,
                "average_score": round(stat.avg_score, 1)
            })

    student_list.sort(key=lambda x: x["average_score"], reverse=True)

    top_students = student_list[:5]
    weak_students = student_list[-5:] if len(student_list) > 5 else student_list

    return {
        "class": {
            "id": class_obj.id,
            "name": class_obj.name
        },
        "summary": {
            "total_exams": total_exams,
            "total_students": total_students,
            "average_score": round(average_score, 1)
        },
        "subject_analysis": subject_analysis_list,
        "score_distribution": score_distribution,
        "top_students": top_students,
        "weak_students": weak_students
    }


@router.get("/comparison")
def compare_class(
    class_id: int,
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """对比班级成绩"""
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return {"error": "班级不存在"}

    query = db.query(Score).filter(Score.class_id == class_id)
    if semester:
        query = query.filter(Score.semester == semester)

    scores = query.all()

    if not scores:
        return {
            "class_avg": 0,
            "grade_avg": 0,
            "comparison": 0
        }

    valid_scores = [s for s in scores if s.score]
    class_avg = sum(s.score for s in valid_scores) / len(valid_scores) if valid_scores else 0

    grade_scores = db.query(Score).filter(Score.score.isnot(None)).all()
    if semester:
        grade_scores = [s for s in grade_scores if s.semester == semester]

    grade_valid = [s for s in grade_scores if s.score]
    grade_avg = sum(s.score for s in grade_valid) / len(grade_valid) if grade_valid else 0

    comparison = class_avg - grade_avg

    return {
        "class_avg": round(class_avg, 1),
        "grade_avg": round(grade_avg, 1),
        "comparison": round(comparison, 1),
        "status": "above" if comparison > 0 else "below" if comparison < 0 else "equal"
    }
