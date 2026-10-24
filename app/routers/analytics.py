from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
import statistics
from app.database import get_db
from app.models import Score, Student, Subject, Class, User, ExamFullScore
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids
from app.scoring import (
    resolve_full_score, materialize_exam_full_scores,
    _exam_date_key, EXCELLENT_RATE_LINE, PASS_RATE_LINE, LOW_RATE_LINE
)
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/analytics", tags=["成绩分析"])

# 临界生：距优秀/及格线的得分率分差（百分点）
CRITICAL_GAP = 5


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

    # ---- 汇总统计（个人折算平均分/得分率口径，满分异构时可比） ----
    valid_scores = [s for s in scores if s.score is not None]
    student_full_map = _full_score_map(db, valid_scores, default_class_id=student.class_id)

    def _norm(s):
        full = student_full_map.get(s.subject_id, 100) or 100
        return s.score / full * 100

    norm_values = [_norm(s) for s in valid_scores]
    average_score = sum(norm_values) / len(norm_values) if norm_values else 0
    max_s = max(valid_scores, key=_norm)
    min_s = min(valid_scores, key=_norm)
    summary = {
        "total_exams": len(exams),
        "max_score": max_s.score,
        "max_score_subject": subject_names.get(max_s.subject_id),
        "min_score": min_s.score,
        "min_score_subject": subject_names.get(min_s.subject_id),
        "average_score": round(average_score, 1)
    }

    # ---- 科目分析（学期内所有考试：原始均分/最高/最低 + 生效满分 + 得分率） ----
    subject_groups = {}
    for s in valid_scores:
        subject_groups.setdefault(s.subject_id, []).append(s.score)
    subject_analysis = []
    for sid, v in subject_groups.items():
        full = student_full_map.get(sid, 100)
        norm_v = [x / (full or 100) * 100 for x in v]
        subject_analysis.append({
            "subject_id": sid,
            "subject_name": subject_names.get(sid),
            "full_score": full,
            "avg_score": round(sum(v) / len(v), 1),
            "score_rate": round(sum(norm_v) / len(norm_v), 1),
            "max_score": max(v),
            "min_score": min(v),
            "exam_count": len(v)
        })
    subject_analysis.sort(key=lambda x: x["subject_name"] or "")

    # ---- 排名趋势：每次考试按班级折算总分排名 ----
    class_scores_query = db.query(Score).filter(Score.class_id == student.class_id)
    if semester:
        class_scores_query = class_scores_query.filter(Score.semester == semester)
    class_scores = class_scores_query.all()

    class_exam_totals = {}  # exam_key -> {"_full": {subject: 满分}, "students": {sid: 折算总分}}
    for s in class_scores:
        k = _exam_key(s)
        if k not in class_exam_totals:
            exam_rows = [x for x in class_scores if _exam_key(x) == k]
            class_exam_totals[k] = {
                "_full": _full_score_map(db, exam_rows, default_class_id=student.class_id),
                "students": {}
            }
        full = class_exam_totals[k]["_full"].get(s.subject_id, 100) or 100
        bucket = class_exam_totals[k]["students"]
        bucket[s.student_id] = bucket.get(s.student_id, 0) + (s.score or 0) / full * 100

    rank_trend = []
    for e, detail in zip(exams, exam_details):
        totals = (class_exam_totals.get(e["key"]) or {}).get("students") or {}
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

    # ---- 薄弱科目：折算得分率低于个人折算平均 5 个百分点以上，按差距降序 ----
    weak_subjects = []
    for sa in subject_analysis:
        gap = round(average_score - sa["score_rate"], 1)
        if gap >= 5:
            weak_subjects.append({
                "subject_id": sa["subject_id"],
                "subject_name": sa["subject_name"],
                "avg_score": sa["avg_score"],
                "score_rate": sa["score_rate"],
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

    # 折算口径（得分率）：分布与均分在满分异构时保持可比
    full_map = _full_score_map(db, valid_scores, default_class_id=class_id)
    norm_values = [s.score / (full_map.get(s.subject_id, 100) or 100) * 100 for s in valid_scores]
    average_score = sum(norm_values) / len(norm_values) if norm_values else 0

    score_distribution = {
        "excellent": len([v for v in norm_values if v >= 90]),
        "good": len([v for v in norm_values if 80 <= v < 90]),
        "average": len([v for v in norm_values if 70 <= v < 80]),
        "pass": len([v for v in norm_values if 60 <= v < 70]),
        "fail": len([v for v in norm_values if v < 60])
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
            "full_score": full_map.get(stat.subject_id, 100),
            "score_rate": round((stat.avg_score or 0) / (full_map.get(stat.subject_id, 100) or 100) * 100, 1),
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
    # 折算口径：班级均分与全校均分统一为得分率（0-100）
    class_full_map = _full_score_map(db, valid_scores, default_class_id=class_id)
    class_avg = sum(
        s.score / (class_full_map.get(s.subject_id, 100) or 100) * 100 for s in valid_scores
    ) / len(valid_scores) if valid_scores else 0

    grade_scores = db.query(Score).filter(Score.score.isnot(None)).all()
    if semester:
        grade_scores = [s for s in grade_scores if s.semester == semester]

    grade_valid = [s for s in grade_scores if s.score]
    grade_full_map = _full_score_map(db, grade_valid)
    grade_avg = sum(
        s.score / (grade_full_map.get(s.subject_id, 100) or 100) * 100 for s in grade_valid
    ) / len(grade_valid) if grade_valid else 0

    comparison = class_avg - grade_avg

    return {
        "class_avg": round(class_avg, 1),
        "grade_avg": round(grade_avg, 1),
        "comparison": round(comparison, 1),
        "status": "above" if comparison > 0 else "below" if comparison < 0 else "equal"
    }


# ==================== 考试报告（以一场考试为中心的班级成绩报告） ====================

def _load_class_scores(db: Session, class_id: int, semester: Optional[str]):
    """加载班级某学期全部成绩，按考试 key 分组并按时间排序"""
    query = db.query(Score).filter(Score.class_id == class_id)
    if semester:
        query = query.filter(Score.semester == semester)
    scores = query.all()

    exam_map = {}
    for s in scores:
        k = _exam_key(s)
        if k not in exam_map:
            exam_map[k] = {
                "key": k,
                "exam_type": s.exam_type,
                "date": _exam_sort_tuple(s)[0],
                "label": _exam_label(s),
                "scores": []
            }
        exam_map[k]["scores"].append(s)
    exams = sorted(exam_map.values(), key=lambda e: (e["date"], e["exam_type"]))
    return exams


def _std(values):
    """样本标准差（人数不足 2 时记 0）"""
    return round(statistics.stdev(values), 1) if len(values) >= 2 else 0


def _rates(values):
    """按得分率（百分制折算分）口径计算三率（返回百分比，保留 1 位小数）"""
    n = len(values)
    if n == 0:
        return 0, 0, 0
    excellent = len([v for v in values if v >= EXCELLENT_RATE_LINE]) / n * 100
    pass_ = len([v for v in values if v >= PASS_RATE_LINE]) / n * 100
    low = len([v for v in values if v < LOW_RATE_LINE]) / n * 100
    return round(excellent, 1), round(pass_, 1), round(low, 1)


def _full_score_map(db: Session, scores, default_class_id=None):
    """一批成绩 → {subject_id: 生效满分}（同场同科满分一致，取首次解析，带缓存）"""
    full_map = {}
    for s in scores:
        if s.subject_id not in full_map:
            full_map[s.subject_id] = resolve_full_score(
                db, s.subject_id, s.exam_type, s.exam_date,
                s.class_id if s.class_id else default_class_id)
    return full_map


def _exam_totals(exam_scores, full_map):
    """一场考试 → {student_id: {total 原始总分, norm_total 折算总分, count 科目数, avg, norm_avg}}"""
    totals = {}
    for s in exam_scores:
        entry = totals.setdefault(s.student_id, {"total": 0.0, "norm_total": 0.0, "count": 0})
        full = full_map.get(s.subject_id, 100) or 100
        entry["total"] += s.score or 0
        entry["norm_total"] += (s.score or 0) / full * 100
        entry["count"] += 1
    for entry in totals.values():
        entry["avg"] = round(entry["total"] / entry["count"], 1) if entry["count"] else 0
        entry["norm_avg"] = round(entry["norm_total"] / entry["count"], 1) if entry["count"] else 0
    return totals


def _rank_map(totals):
    """{student_id: 名次}，按折算总分降序（满分不同时原始总分不可比），同分同名次"""
    rank_map = {}
    sorted_items = sorted(totals.items(), key=lambda kv: kv[1]["norm_total"], reverse=True)
    prev_total, prev_rank = None, 0
    for idx, (sid, entry) in enumerate(sorted_items, start=1):
        rank = prev_rank if entry["norm_total"] == prev_total else idx
        rank_map[sid] = rank
        prev_total, prev_rank = entry["norm_total"], rank
    return rank_map


@router.get("/exams")
def list_class_exams(
    class_id: int,
    semester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """班级考试列表（考试 = 考试类型+日期 聚合），供考试报告下拉选择"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")

    exams = _load_class_scores(db, class_id, semester)
    return [
        {
            "key": e["key"],
            "label": e["label"],
            "exam_type": e["exam_type"],
            "date": e["date"],
            "student_count": len({s.student_id for s in e["scores"]}),
            "record_count": len(e["scores"])
        }
        for e in exams
    ]


@router.get("/exam-report")
def get_exam_report(
    class_id: int,
    semester: str,
    exam_key: str = Query(..., description="考试标识（考试类型|日期，来自 /exams）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """班级考试报告：核心指标 / 各科三率 / 分数段 / 进退步 / 临界生 / 科目均衡"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")

    exams = _load_class_scores(db, class_id, semester)
    exam = next((e for e in exams if e["key"] == exam_key), None)
    if not exam:
        raise HTTPException(status_code=404, detail="该学期下未找到此考试")

    exam_scores = exam["scores"]
    subject_names = {}
    for s in exam_scores:
        if s.subject_id not in subject_names:
            subj = db.query(Subject).filter(Subject.id == s.subject_id).first()
            subject_names[s.subject_id] = subj.name if subj else f"科目{s.subject_id}"

    students = {s.id: s.name for s in db.query(Student).filter(Student.class_id == class_id).all()}

    # 该场各科生效满分（三层模型）
    full_map = _full_score_map(db, exam_scores, default_class_id=class_id)

    totals = _exam_totals(exam_scores, full_map)
    # 折算平均分（得分率口径，0-100）：summary/分段/临界生统一使用
    avgs = [entry["norm_avg"] for entry in totals.values()]

    # ---- 核心指标（按个人折算平均分/得分率，满分异构时口径统一） ----
    er, pr, lr = _rates(avgs)
    summary = {
        "student_count": len(totals),
        "record_count": len(exam_scores),
        "avg": round(sum(avgs) / len(avgs), 1) if avgs else 0,
        "median": round(statistics.median(avgs), 1) if avgs else 0,
        "max": round(max(avgs), 1) if avgs else 0,
        "min": round(min(avgs), 1) if avgs else 0,
        "std_dev": _std(avgs),
        "excellent_rate": er,
        "pass_rate": pr,
        "low_rate": lr
    }

    # ---- 全校同场考试各科均分（折算为得分率口径，科目均衡对照） ----
    same_semester_scores = db.query(Score).filter(Score.semester == semester).all()
    grade_subject_scores = {}
    for s in same_semester_scores:
        if _exam_key(s) == exam_key and s.score is not None:
            grade_subject_scores.setdefault(s.subject_id, []).append(s)
    grade_norm_avg = {}
    for sid, rows in grade_subject_scores.items():
        g_full_map = _full_score_map(db, rows)
        pcts = [r.score / (g_full_map.get(sid, 100) or 100) * 100 for r in rows]
        grade_norm_avg[sid] = round(sum(pcts) / len(pcts), 1) if pcts else None

    # ---- 各科指标表（原始分 + 满分 + 得分率三率 + 录入的年级均分参照） ----
    from app.models import GradeSubjectAverage
    entered_grade_avgs = {}
    if exam["date"]:
        d = _exam_date_key(exam["date"])
        for g in db.query(GradeSubjectAverage).filter(
            GradeSubjectAverage.semester == semester,
            GradeSubjectAverage.exam_type == exam["exam_type"],
            GradeSubjectAverage.exam_date == d
        ).all():
            entered_grade_avgs[g.subject_id] = g.avg_score

    subjects_report = []
    by_subject = {}
    for s in exam_scores:
        if s.score is None:
            continue
        by_subject.setdefault(s.subject_id, []).append(s.score)
    for sid, values in by_subject.items():
        full = full_map.get(sid, 100)
        norm_values = [v / (full or 100) * 100 for v in values]
        s_er, s_pr, s_lr = _rates(norm_values)
        subjects_report.append({
            "subject_id": sid,
            "subject_name": subject_names.get(sid),
            "full_score": full,
            "avg": round(sum(values) / len(values), 1),
            "score_rate": round(sum(norm_values) / len(norm_values), 1),
            "max": round(max(values), 1),
            "min": round(min(values), 1),
            "std_dev": _std(values),
            "excellent_rate": s_er,
            "pass_rate": s_pr,
            "low_rate": s_lr,
            # 按库内数据计算的全校得分率（口径一致可直接对比）
            "grade_avg": grade_norm_avg.get(sid),
            # 人工录入的年级平均分（原始分，联考参照），无录入为 None
            "grade_avg_entered": entered_grade_avgs.get(sid)
        })
    subjects_report.sort(key=lambda x: x["subject_name"] or "")

    # ---- 分数段（个人平均分，10 分一段） ----
    segments = []
    for low in range(90, -1, -10):
        high = low + 10
        label = f"{low}-{high if high <= 100 else 100}"
        count = len([v for v in avgs if low <= v < high or (high == 100 and v == 100)])
        segments.append({"label": label, "count": count})

    # ---- 名次表 + 与上一场考试的进退步（按折算总分排名） ----
    idx = exams.index(exam)
    prev_exam = exams[idx - 1] if idx > 0 else None
    prev_rank_map = _rank_map(_exam_totals(prev_exam["scores"], _full_score_map(db, prev_exam["scores"], class_id))) if prev_exam else {}

    # 每学生各科原始分（供前端「单科名次」按科目排序查看）
    student_subject_scores = {}
    for s in exam_scores:
        student_subject_scores.setdefault(s.student_id, {})[subject_names.get(s.subject_id, f"科目{s.subject_id}")] = s.score

    rank_map = _rank_map(totals)
    rankings = []
    for sid, entry in totals.items():
        prev_rank = prev_rank_map.get(sid)
        rankings.append({
            "student_id": sid,
            "student_name": students.get(sid, f"学生{sid}"),
            "total_score": round(entry["total"], 1),
            "norm_total": round(entry["norm_total"], 1),
            "avg_score": entry["avg"],
            "norm_avg": entry["norm_avg"],
            "subject_scores": student_subject_scores.get(sid, {}),
            "rank": rank_map[sid],
            "prev_rank": prev_rank,
            # 正数 = 进步名次数，负数 = 退步，None = 上场缺考/无上场考试
            "rank_change": (prev_rank - rank_map[sid]) if prev_rank is not None else None
        })
    rankings.sort(key=lambda x: x["rank"])

    # ---- 临界生（个人折算平均分距线 ≤5 个百分点） ----
    def _critical(lo, hi, line):
        items = [
            {"student_id": sid, "student_name": students.get(sid, f"学生{sid}"),
             "avg_score": entry["norm_avg"], "gap": round(line - entry["norm_avg"], 1)}
            for sid, entry in totals.items() if lo <= entry["norm_avg"] < hi
        ]
        items.sort(key=lambda x: x["avg_score"], reverse=True)
        return items

    critical = {
        "excellence": _critical(EXCELLENT_RATE_LINE - CRITICAL_GAP, EXCELLENT_RATE_LINE, EXCELLENT_RATE_LINE),
        "pass": _critical(PASS_RATE_LINE - CRITICAL_GAP, PASS_RATE_LINE, PASS_RATE_LINE)
    }

    # ---- 科目均衡（班级 vs 年级，得分率）：年级线优先用录入的年级均分，无则按库内数据计算 ----
    def _grade_line(x):
        if x["grade_avg_entered"] is not None:
            full = x["full_score"] or 100
            return round(x["grade_avg_entered"] / full * 100, 1)
        return x["grade_avg"]

    balance = {
        "subjects": [x["subject_name"] for x in subjects_report],
        "class_avg": [x["score_rate"] for x in subjects_report],
        "grade_avg": [_grade_line(x) for x in subjects_report]
    }

    return {
        "exam": {"key": exam["key"], "label": exam["label"],
                 "exam_type": exam["exam_type"], "date": exam["date"]},
        "prev_exam": {"key": prev_exam["key"], "label": prev_exam["label"]} if prev_exam else None,
        "summary": summary,
        "subjects": subjects_report,
        "segments": segments,
        "rankings": rankings,
        "critical": critical,
        "balance": balance
    }


# ==================== 场次满分（考试报告配套） ====================

@router.put("/exam-full-score")
def upsert_exam_full_score(
    class_id: int,
    subject_id: int,
    exam_type: str = Query(...),
    exam_date: str = Query(..., description="考试日期 YYYY-MM-DD"),
    full_score: float = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """设置某场考试某科目的实际满分（场次实例级，优先级最高，覆盖类型/科目默认）"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    d = _exam_date_key(exam_date)
    if d is None:
        raise HTTPException(status_code=400, detail="考试日期格式错误，应为 YYYY-MM-DD")

    row = db.query(ExamFullScore).filter(
        ExamFullScore.class_id == class_id,
        ExamFullScore.subject_id == subject_id,
        ExamFullScore.exam_type == exam_type,
        ExamFullScore.exam_date == d
    ).first()
    if row:
        row.full_score = full_score
    else:
        row = ExamFullScore(
            class_id=class_id, subject_id=subject_id,
            exam_type=exam_type, exam_date=d, full_score=full_score
        )
        db.add(row)
    db.commit()
    return {"message": f"已设置 {subject.name} 本场满分为 {full_score}", "full_score": full_score}


@router.delete("/exam-full-score")
def delete_exam_full_score(
    class_id: int,
    subject_id: int,
    exam_type: str = Query(...),
    exam_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """清除场次实例满分（回落到考试类型默认 → 科目默认）"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")

    d = _exam_date_key(exam_date)
    row = db.query(ExamFullScore).filter(
        ExamFullScore.class_id == class_id,
        ExamFullScore.subject_id == subject_id,
        ExamFullScore.exam_type == exam_type,
        ExamFullScore.exam_date == d
    ).first() if d else None
    if row:
        db.delete(row)
        db.commit()
    fallback = resolve_full_score(db, subject_id, exam_type, d, class_id)
    return {"message": "已清除，回落到上层默认", "full_score": fallback}
