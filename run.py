"""
班主任工作台 —— 一键启动脚本

快速部署（迁移给他人使用）：
    python run.py                # 自动初始化数据库（首次）并启动后端服务

常用参数：
    python run.py --host 192.168.1.7 --port 8001 --reload
    python run.py --init-only    # 仅初始化数据库，不启动服务
    python run.py --reset-db     # 清空数据库后重新初始化（危险！会删除全部数据）

初始化内容：
    1. 按当前 ORM 模型创建全部数据表（幂等，缺啥建啥）
    2. 种子数据（仅在缺失时写入，不改动已有数据）：
       - 管理员 admin/admin123、班主任 teacher1/123456
       - 班级「管理班级」（七年级）
       - 13 个标准科目 + 班级科目配置
       - 学期「2026-2」
       - 学生与期末成绩：读取项目根目录的 七下期末.xlsx
         （8 个计分科目：语文/数学/英语/生物/地理/道德与法治/历史/体）

前端启动（frontend 目录）：
    npm install
    npm run dev
"""

import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ==================== 可按需调整的种子配置 ====================
CLASS_NAME = "管理班级"        # 种子班级名称（对应 七下期末.xlsx 中 班级=9 的学生）
CLASS_GRADE = 7                # 七年级
SEMESTER_NAME = "2026-2"       # 成绩所属学期（沿用系统当前学期命名）
SEMESTER_YEAR = 2026
EXAM_TYPE = "期末考试"         # 七下期末
EXAM_DATE = datetime(2026, 6, 30)  # 考试日期（趋势图横轴排序依据）
XLSX_PATH = os.path.join(BASE_DIR, "七下期末.xlsx")

# 计分科目（xlsx 中有数值成绩的列）与展示科目（仅等级，不计分）
SCORE_SUBJECTS = ["语文", "数学", "英语", "生物", "地理", "道德与法治", "历史", "体"]
GRADE_ONLY_SUBJECTS = ["音", "美", "信", "口", "书"]
STANDARD_SUBJECTS = SCORE_SUBJECTS + GRADE_ONLY_SUBJECTS


def init_database(reset: bool = False, with_xlsx: bool = True) -> None:
    from app.database import engine, Base, SessionLocal
    import app.models  # noqa: F401 确保所有模型注册到 Base

    if reset:
        print("[init] 正在清空数据库（drop_all）...")
        Base.metadata.drop_all(bind=engine)
    print("[init] 创建/校验数据表（对齐当前 ORM 模型）...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_users(db)
        _seed_subjects(db)
        _seed_semester(db)
        cls = _seed_class(db)
        _seed_class_subjects(db, cls)
        if with_xlsx:
            _seed_students_and_scores(db, cls)
        db.commit()
        print("[init] 数据库初始化完成。")
    except Exception as e:
        db.rollback()
        print(f"[init] 初始化失败: {e}")
        raise
    finally:
        db.close()


def _seed_users(db):
    from app.models import User
    from app.auth import get_password_hash

    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            real_name="系统管理员",
            role="admin",
            is_active=True,
        ))
        print("[init] 已创建管理员账号 admin/admin123")

    if not db.query(User).filter(User.username == "teacher1").first():
        db.add(User(
            username="teacher1",
            hashed_password=get_password_hash("123456"),
            real_name="测试班主任",
            role="class_teacher",
            is_active=True,
        ))
        print("[init] 已创建班主任账号 teacher1/123456")
    db.flush()  # autoflush=False，显式 flush 让后续查询可见


def _seed_subjects(db):
    from app.models import Subject
    existing = {s.name for s in db.query(Subject).all()}
    for name in STANDARD_SUBJECTS:
        if name not in existing:
            db.add(Subject(name=name))
    db.flush()
    if len(existing) < len(STANDARD_SUBJECTS):
        print(f"[init] 已补齐标准科目（共 {len(STANDARD_SUBJECTS)} 个）")


def _seed_semester(db):
    from app.models import Semester
    if not db.query(Semester).filter(Semester.name == SEMESTER_NAME).first():
        db.add(Semester(name=SEMESTER_NAME, year=SEMESTER_YEAR, is_active=True))
        print(f"[init] 已创建学期 {SEMESTER_NAME}")


def _seed_class(db):
    from app.models import Class
    cls = db.query(Class).filter(Class.name == CLASS_NAME).first()
    if not cls:
        cls = Class(name=CLASS_NAME, grade=CLASS_GRADE)
        db.add(cls)
        db.flush()
        print(f"[init] 已创建班级 {CLASS_NAME}（{CLASS_GRADE}年级）")
        # 将种子班主任绑定到该班级
        from app.models import User
        teacher1 = db.query(User).filter(User.username == "teacher1").first()
        if teacher1 and not teacher1.class_id:
            teacher1.class_id = cls.id
    return cls


def _seed_class_subjects(db, cls):
    """为种子班级配置全部标准科目：计分科目 is_score_related=True，等级科目 False"""
    from app.models import Subject, ClassSubject
    subjects = {s.name: s for s in db.query(Subject).all()}
    existing = {
        cs.subject_id for cs in db.query(ClassSubject).filter(ClassSubject.class_id == cls.id)
    }
    added = 0
    for name in STANDARD_SUBJECTS:
        subject = subjects.get(name)
        if not subject or subject.id in existing:
            continue
        db.add(ClassSubject(
            class_id=cls.id,
            subject_id=subject.id,
            teacher_id=None,
            is_teaching=True,
            is_score_related=name in SCORE_SUBJECTS,
        ))
        added += 1
    if added:
        print(f"[init] 已为班级 {CLASS_NAME} 配置 {added} 个科目（计分 {len(SCORE_SUBJECTS)} 个）")


def _read_xlsx():
    """读取 七下期末.xlsx，返回 [(student_no, name, {科目: 分数}), ...]"""
    import openpyxl
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c).strip() if c is not None else "" for c in rows[0]]

    idx_no = header.index("学号")
    idx_name = header.index("姓名")
    subject_cols = {}
    for name in SCORE_SUBJECTS:
        if name in header:
            subject_cols[name] = header.index(name)

    students = []
    for row in rows[1:]:
        if row is None or row[idx_name] is None:
            continue
        no = str(row[idx_no]).strip() if row[idx_no] is not None else ""
        name = str(row[idx_name]).strip()
        if not name:
            continue
        scores = {s: float(row[i]) for s, i in subject_cols.items()
                  if row[i] is not None and isinstance(row[i], (int, float))}
        students.append((no, name, scores))
    wb.close()
    return students


def _seed_students_and_scores(db, cls):
    from app.models import Student, Subject, Score
    from sqlalchemy import func

    if not os.path.exists(XLSX_PATH):
        print(f"[init] 未找到 {XLSX_PATH}，跳过学生与成绩种子。")
        return

    xlsx_students = _read_xlsx()
    if not xlsx_students:
        print("[init] 七下期末.xlsx 无有效数据，跳过。")
        return

    # 学生：按学号幂等写入
    existing_nos = {s.student_no for s in db.query(Student).filter(Student.class_id == cls.id)}
    student_map = {s.student_no: s for s in db.query(Student).filter(Student.class_id == cls.id)}
    added = 0
    for no, name, _scores in xlsx_students:
        if no and no in existing_nos:
            continue
        stu = Student(name=name, student_no=no or None, class_id=cls.id)
        db.add(stu)
        db.flush()
        student_map[no] = stu
        added += 1
    if added:
        print(f"[init] 已从 xlsx 导入 {added} 名学生到 {CLASS_NAME}")

    # 成绩：仅当该班级此学期无成绩时写入（不重复导入）
    score_count = db.query(func.count()).select_from(Score).filter(
        Score.class_id == cls.id, Score.semester == SEMESTER_NAME
    ).scalar()
    if score_count:
        print(f"[init] 班级 {CLASS_NAME} 学期 {SEMESTER_NAME} 已有 {score_count} 条成绩，跳过成绩种子。")
        return

    subjects = {s.name: s for s in db.query(Subject).all()}
    inserted = 0
    for no, name, scores in xlsx_students:
        stu = student_map.get(no)
        if not stu:
            continue
        for subject_name, val in scores.items():
            subject = subjects.get(subject_name)
            if not subject:
                continue
            db.add(Score(
                student_id=stu.id,
                subject_id=subject.id,
                class_id=cls.id,
                score=val,
                exam_type=EXAM_TYPE,
                exam_date=EXAM_DATE,
                semester=SEMESTER_NAME,
            ))
            inserted += 1
    db.flush()
    print(f"[init] 已写入 {EXAM_TYPE} 成绩 {inserted} 条（学期 {SEMESTER_NAME}，科目 {len(SCORE_SUBJECTS)} 个）")


def main():
    parser = argparse.ArgumentParser(description="班主任工作台一键启动脚本")
    parser.add_argument("--host", default="192.168.1.7", help="监听地址（默认 0.0.0.0，支持局域网访问）")
    parser.add_argument("--port", type=int, default=8001, help="监听端口（默认 8001）")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    parser.add_argument("--init-only", action="store_true", help="仅初始化数据库，不启动服务")
    parser.add_argument("--reset-db", action="store_true", help="清空数据库后重新初始化（危险！）")
    parser.add_argument("--no-xlsx", action="store_true", help="初始化时跳过七下期末.xlsx 种子数据")
    args = parser.parse_args()

    init_database(reset=args.reset_db, with_xlsx=not args.no_xlsx)

    if args.init_only:
        return

    import uvicorn
    print(f"[run] 启动后端服务: http://{args.host}:{args.port}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
