"""
班主任工作台 —— 一键启动脚本

快速部署（迁移给他人使用）：
    python run.py                # 自动初始化数据库（首次）并启动后端服务

地址与端口默认读取项目根目录的统一配置文件 .env（含 SERVER_IP、端口、数据库连接等，
换办公地点只需修改 .env 中的 SERVER_IP 一处），详见《部署指南.md》。

公网访问（临时远程测试）：
    .env 中 PUBLIC_ACCESS=true + 填入 CPOLAR_AUTHTOKEN 后启动本脚本，
    自动通过 cpolar 建立公网隧道（免费版随机地址，重启变化），详见《部署指南.md》。

常用参数：
    python run.py --reload       # 开发模式热重载
    python run.py --host 0.0.0.0 --port 8001   # 临时覆盖 .env 中的地址/端口
    python run.py --init-only    # 仅初始化数据库，不启动服务
    python run.py --reset-db     # 清空数据库后重新初始化（危险！会删除全部数据）

初始化内容：
    1. 数据表：全新/历史库按 ORM 模型 create_all 后登记 alembic 版本；
       已接入 alembic 的库执行 alembic upgrade head 应用增量迁移
       （改模型后请先 alembic revision --autogenerate 生成迁移脚本）
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
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ==================== 可按需调整的种子配置 ====================
CLASS_NAME = "管理班级"        # 种子班级名称（对应 七下期末.xlsx 中 班级=9 的学生）
CLASS_GRADE = 7                # 七年级
SEMESTER_NAME = "2026-2"       # 成绩所属学期（沿用系统当前学期命名）
SEMESTER_YEAR = 2026
EXAM_TYPE = "期末考试"         # 七下期末
EXAM_DATE = date(2026, 6, 30)  # 考试日期（趋势图横轴排序依据）
XLSX_PATH = os.path.join(BASE_DIR, "七下期末.xlsx")

# 计分科目（xlsx 中有数值成绩的列）与展示科目（仅等级，不计分）
SCORE_SUBJECTS = ["语文", "数学", "英语", "生物", "地理", "道德与法治", "历史", "体"]
GRADE_ONLY_SUBJECTS = ["音", "美", "信", "口", "书"]
STANDARD_SUBJECTS = SCORE_SUBJECTS + GRADE_ONLY_SUBJECTS


def _run_alembic(action: str) -> None:
    """以编程方式执行 alembic 命令（"upgrade" = 升级到最新版本，"stamp" = 仅登记当前版本）"""
    try:
        from alembic import command as alembic_command
        from alembic.config import Config as AlembicConfig
    except ImportError:
        raise RuntimeError("缺少 alembic 依赖（数据库迁移），请执行: pip install -r requirements.txt")

    cfg = AlembicConfig(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    if action == "upgrade":
        alembic_command.upgrade(cfg, "head")
    else:
        alembic_command.stamp(cfg, "head")


def _alembic_state(engine) -> str:
    """判断数据库与 alembic 的关系："managed" / "legacy" / "fresh"

    - managed：alembic_version 存在且版本号在当前迁移目录中 → 增量升级
    - legacy：alembic_version 存在但版本号无法识别（早期试验遗留），
              或版本号为空 → 按历史库处理：create_all 校准后重新登记
    - fresh：没有 alembic_version（全新库或一直用 create_all 的库）
    """
    from alembic.config import Config as AlembicConfig
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    cfg = AlembicConfig(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    known = {rev.revision for rev in ScriptDirectory.from_config(cfg).walk_revisions()}

    with engine.connect() as conn:
        stored = [row[0] for row in conn.execute(text("SELECT version_num FROM alembic_version"))]
    if stored and stored[0] in known:
        return "managed"
    return "legacy"


def init_database(reset: bool = False, with_xlsx: bool = True) -> None:
    from sqlalchemy import inspect, text
    from app.database import engine, Base, SessionLocal
    import app.models  # noqa: F401 确保所有模型注册到 Base

    if reset:
        print("[init] 正在清空数据库（drop_all）...")
        Base.metadata.drop_all(bind=engine)

    if "alembic_version" in inspect(engine).get_table_names() and _alembic_state(engine) == "managed":
        # 已接入 alembic 的库：只按迁移脚本演进
        # （create_all 处理不了改列类型/删列/改约束，这些只能靠迁移脚本）
        print("[init] 应用数据库迁移（alembic upgrade head）...")
        _run_alembic("upgrade")
    else:
        # 全新库 / 历史库 / 遗留版本号：create_all 建齐缺表（对已有表幂等），
        # 然后登记为当前版本；之后的结构变更用 alembic revision --autogenerate 生成迁移脚本
        if "alembic_version" in inspect(engine).get_table_names():
            # 早期试验遗留的版本号当前迁移目录不认识，stamp 前需清掉
            print("[init] 检测到无法识别的 alembic 历史版本号，清除后重新登记...")
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM alembic_version"))
        print("[init] 创建/校验数据表（对齐当前 ORM 模型）...")
        Base.metadata.create_all(bind=engine)
        _run_alembic("stamp")

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


def _start_public_tunnels():
    """PUBLIC_ACCESS=true 时通过 cpolar 为两个前端端口建立公网隧道，返回子进程列表。

    仅映射前端端口（班主任端/家长端）：远程浏览器访问 cpolar 公网地址 -> 本机 vite ->
    vite 将 /api 代理到本机后端，后端与数据库不直接暴露公网。
    cpolar 免费版：随机公网地址（每次重启变化）、限速 1Mbps、最多 4 条隧道。
    """
    import re
    import shutil
    import subprocess
    import threading

    from app.config import settings

    if not settings.PUBLIC_ACCESS:
        return []

    print("[public] 公网访问模式已开启（.env PUBLIC_ACCESS=true，测试完请改回 false）")
    # 定位 cpolar：优先 PATH，其次项目内便携版 tools\cpolar\cpolar.exe
    candidates = []
    for p in [shutil.which("cpolar"),
              os.path.join(BASE_DIR, "tools", "cpolar", "cpolar.exe"),
              r"C:\Program Files\cpolar\cpolar.exe",
              r"C:\Program Files (x86)\cpolar\cpolar.exe"]:
        if p and os.path.exists(p):
            candidates.append(p)
    if not candidates:
        print("[public] 警告: 未找到 cpolar（已尝试 PATH、tools\\cpolar\\cpolar.exe 及默认安装目录）")
        print("[public]   请到 https://www.cpolar.com/download 下载 Windows 版，")
        print("[public]   或将 cpolar.exe 放到项目 tools\\cpolar\\ 目录下，然后重启")
        return []
    cpolar = candidates[0]

    if not settings.CPOLAR_AUTHTOKEN:
        print("[public] 警告: .env 中 CPOLAR_AUTHTOKEN 为空，跳过公网隧道（仅本地启动）")
        print("[public]   请到 https://www.cpolar.com 注册账号，")
        print("[public]   登录 https://dashboard.cpolar.com 在「验证」页复制 authtoken 填入 .env 后重启")
        return []

    # 写入 authtoken（幂等，cpolar 会保存到自身配置文件）
    r = subprocess.run([cpolar, "authtoken", settings.CPOLAR_AUTHTOKEN],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[public] 警告: cpolar authtoken 配置失败: {(r.stdout or r.stderr or '').strip()}")

    procs = []
    for label, port in [("班主任端", settings.FRONTEND_PORT), ("家长端", settings.PARENT_PORT)]:
        try:
            # -log stdout: 管道模式下 cpolar 才会输出隧道日志（含公网地址），
            # 否则仅交互终端显示 TUI 横幅，子进程捕获不到任何输出
            p = subprocess.Popen(
                [cpolar, "http", str(port), "-log", "stdout", "-log-level", "INFO"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=BASE_DIR,
            )
        except Exception as e:
            print(f"[public] 警告: 启动 {label} 隧道失败: {e}")
            continue
        procs.append(p)

        # 后台线程解析公网地址（-log stdout 模式输出 "Tunnel established at <url>"，
        # 交互终端模式输出含 "->" 的 Forwarding 行，两种都兼容）
        def watch(p=p, label=label):
            found = set()
            try:
                for line in p.stdout:
                    if "Tunnel established at" not in line and "->" not in line:
                        continue
                    m = re.search(r"https?://[^\s'\"]+", line)
                    if m and m.group(0) not in found:
                        print(f"[public] {label} 公网地址: {m.group(0)}", flush=True)
                        found.add(m.group(0))
                if not found and p.poll() is not None:
                    print(f"[public] 警告: {label} 隧道已退出（请检查 authtoken 是否有效 / 免费版隧道数量是否超限）")
            except Exception:
                pass

        threading.Thread(target=watch, daemon=True).start()
    return procs


def _stop_public_tunnels(procs):
    """退出时清理 cpolar 子进程，避免隧道残留"""
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass


def _detect_lan_ip() -> str:
    """探测本机局域网 IP（探测失败回退 127.0.0.1）"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _ensure_env_file() -> bool:
    """首次运行自动生成 .env（默认 SQLite 免安装 + 随机密钥 + 本机 IP）。

    返回是否新生成。生成后提示用户可按需修改（如切换 PostgreSQL）。
    """
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        return False

    import secrets as _secrets
    from pathlib import Path as _Path
    db_path = (_Path(BASE_DIR) / "ddclass.db").as_posix()
    content = f"""# ============================================================
# DD-CLASS 班级管理系统 统一配置（run.py 首次运行自动生成）
# 零依赖快速体验默认使用 SQLite（免安装）；生产环境建议改用 PostgreSQL：
#   1. 安装 PostgreSQL 并建库：CREATE DATABASE ddclass;
#   2. 将下方 DATABASE_URL 改为 postgresql://用户名:密码@127.0.0.1:5432/ddclass
# 修改本文件后需重启服务生效
# ============================================================

# 本机局域网 IP（自动探测；换网络后改这里）
SERVER_IP={_detect_lan_ip()}

# 服务端口
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3000
PARENT_HOST=0.0.0.0
PARENT_PORT=5174

# 数据库（默认 SQLite 免安装）
DATABASE_URL=sqlite:///{db_path}

# JWT 签名密钥（已自动生成随机值）
SECRET_KEY={_secrets.token_hex(32)}
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 额外允许的跨域来源（一般留空）
CORS_ORIGINS=

# 公网访问（cpolar 内网穿透，临时远程测试用）
PUBLIC_ACCESS=false
CPOLAR_AUTHTOKEN=
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main():
    # 首次运行自动生成 .env（默认 SQLite + 随机密钥 + 本机 IP），必须在导入 app.config 之前
    if _ensure_env_file():
        print("[run] 未检测到 .env，已自动生成（默认 SQLite 免安装 + 随机密钥）")
        print("[run] 生产环境建议编辑 .env 切换 PostgreSQL（文件内有说明）\n")
    from app.config import settings

    parser = argparse.ArgumentParser(description="班主任工作台一键启动脚本")
    parser.add_argument("--host", default=None,
                        help=f"监听地址（默认读根目录 .env 的 BACKEND_HOST，当前 {settings.BACKEND_HOST}）")
    parser.add_argument("--port", type=int, default=None,
                        help=f"监听端口（默认读根目录 .env 的 BACKEND_PORT，当前 {settings.BACKEND_PORT}）")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    parser.add_argument("--init-only", action="store_true", help="仅初始化数据库，不启动服务")
    parser.add_argument("--reset-db", action="store_true", help="清空数据库后重新初始化（危险！）")
    parser.add_argument("--no-xlsx", action="store_true", help="初始化时跳过七下期末.xlsx 种子数据")
    args = parser.parse_args()
    host = args.host or settings.BACKEND_HOST
    port = args.port or settings.BACKEND_PORT

    init_database(reset=args.reset_db, with_xlsx=not args.no_xlsx)

    if args.init_only:
        return

    public_procs = _start_public_tunnels()

    import uvicorn
    ip = settings.SERVER_IP
    print("=" * 56)
    print(f"[run] 后端监听地址: http://{host}:{port}")
    print(f"[run] 局域网访问提示（SERVER_IP={ip}，换网络请修改 .env 后重启）:")
    print(f"[run]   后端 API:  http://{ip}:{port}/")
    print(f"[run]   班主任端:  http://{ip}:{settings.FRONTEND_PORT}/")
    print(f"[run]   家长端:    http://{ip}:{settings.PARENT_PORT}/")
    if settings.PUBLIC_ACCESS:
        print("[run] 公网模式已开启，cpolar 公网地址见上方 [public] 输出（重启后地址变化需重新发送）")
        print("[run] 注意：公网模式仍需照常启动两个前端（start-frontend.bat / start-parent.bat）")
    print("=" * 56)
    try:
        uvicorn.run("app.main:app", host=host, port=port, reload=args.reload)
    finally:
        _stop_public_tunnels(public_procs)


if __name__ == "__main__":
    main()
