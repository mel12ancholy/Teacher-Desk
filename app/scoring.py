"""科目满分解析与得分率口径

满分三层模型（优先级从高到低）：
1. 场次实例：ExamFullScore(class_id, subject_id, exam_type, exam_date)
2. 考试类型默认：ExamTypeFullScore(subject_id, exam_type)
3. 科目默认：Subject.full_score（默认 100）

分析口径统一约定：
- 折算分（百分制）= 原始分 / 该场该科生效满分 * 100
- 优秀线 = 得分率 90%，及格线 = 60%，低分线 = 40%
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import ExamFullScore, ExamTypeFullScore, Subject

DEFAULT_FULL_SCORE = 100.0
EXCELLENT_RATE_LINE = 90   # 得分率 ≥90% 为优秀
PASS_RATE_LINE = 60        # 得分率 ≥60% 为及格
LOW_RATE_LINE = 40         # 得分率 <40% 为低分


def _exam_date_key(exam_date) -> Optional[date]:
    """成绩行的考试日期（datetime/str/date）归一为 date，无日期返回 None"""
    if exam_date is None:
        return None
    if isinstance(exam_date, datetime):
        return exam_date.date()
    if isinstance(exam_date, date):
        return exam_date
    try:
        return datetime.fromisoformat(str(exam_date)).date()
    except (ValueError, TypeError):
        return None


def resolve_full_score(db: Session, subject_id: int, exam_type: str, exam_date, class_id: Optional[int] = None) -> float:
    """解析一条成绩的生效满分（三层回落，带进程级无缓存直查——班级规模小，查询成本可忽略）"""
    # 1. 场次实例
    d = _exam_date_key(exam_date)
    if class_id is not None and d is not None:
        inst = db.query(ExamFullScore).filter(
            ExamFullScore.class_id == class_id,
            ExamFullScore.subject_id == subject_id,
            ExamFullScore.exam_type == exam_type,
            ExamFullScore.exam_date == d
        ).first()
        if inst:
            return float(inst.full_score)
    # 2. 考试类型默认
    by_type = db.query(ExamTypeFullScore).filter(
        ExamTypeFullScore.subject_id == subject_id,
        ExamTypeFullScore.exam_type == exam_type
    ).first()
    if by_type:
        return float(by_type.full_score)
    # 3. 科目默认
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject and subject.full_score:
        return float(subject.full_score)
    return DEFAULT_FULL_SCORE


def materialize_exam_full_scores(db: Session, class_id: int, items) -> None:
    """批量导入后物化场次满分：items 为 (subject_id, exam_type, exam_date) 可迭代。

    已存在实例的不再覆盖（保留教师手工修改）；需调用方 commit。
    """
    seen = set()
    for subject_id, exam_type, exam_date in items:
        d = _exam_date_key(exam_date)
        if d is None:
            continue
        key = (subject_id, exam_type, d)
        if key in seen:
            continue
        seen.add(key)
        exists = db.query(ExamFullScore).filter(
            ExamFullScore.class_id == class_id,
            ExamFullScore.subject_id == subject_id,
            ExamFullScore.exam_type == exam_type,
            ExamFullScore.exam_date == d
        ).first()
        if exists:
            continue
        db.add(ExamFullScore(
            class_id=class_id,
            subject_id=subject_id,
            exam_type=exam_type,
            exam_date=d,
            full_score=resolve_full_score(db, subject_id, exam_type, d, class_id)
        ))


def rate_band(score: float, full_score: float) -> Optional[str]:
    """按得分率分档：excellent / pass / low / None（无效输入）"""
    if score is None or not full_score:
        return None
    pct = score / full_score * 100
    if pct >= EXCELLENT_RATE_LINE:
        return "excellent"
    if pct >= PASS_RATE_LINE:
        return "pass"
    if pct < LOW_RATE_LINE:
        return "low"
    return "middle"


def normalize(score: float, full_score: float) -> float:
    """折算为百分制得分率（满分无效时按 100 处理）"""
    if not full_score:
        full_score = DEFAULT_FULL_SCORE
    return round(score / full_score * 100, 1)


# 常用考试类型（与前端下拉保持一致）
COMMON_EXAM_TYPES = ["期中考试", "期末考试", "月考", "测验", "模拟考试"]
