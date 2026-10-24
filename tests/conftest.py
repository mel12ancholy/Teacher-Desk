"""pytest 公共夹具

测试环境隔离：在导入 app 之前把 DATABASE_URL 指向 tests/_test.db（SQLite），
环境变量优先级高于 .env 文件，因此不会触碰真实 PostgreSQL。
每次 pytest 启动重建该文件，测试之间数据种子保持幂等。
"""

import os
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

_TEST_DB = TESTS_DIR / "_test.db"
_TEST_DB.unlink(missing_ok=True)  # 每次运行全新开始

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-do-not-use-in-prod"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ratelimit  # noqa: E402
from app.auth import get_password_hash  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402  导入即完成建表 + 标准科目种子
from app.models import Class, Student, User  # noqa: E402

# 固定家长码，供家长端测试使用
PARENT_CODE = "TESTAB12"


def _seed() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", hashed_password=get_password_hash("admin123"),
                        real_name="管理员", role="admin", is_active=True))
        if not db.query(User).filter(User.username == "teacher1").first():
            db.add(User(username="teacher1", hashed_password=get_password_hash("123456"),
                        real_name="班主任", role="class_teacher", is_active=True))
        if not db.query(Class).filter(Class.name == "测试班").first():
            db.add(Class(name="测试班", grade=7))
        db.commit()
        cls = db.query(Class).filter(Class.name == "测试班").first()
        if not db.query(Student).filter(Student.parent_code == PARENT_CODE).first():
            db.add(Student(name="测试学生", student_no="T001",
                           class_id=cls.id, parent_code=PARENT_CODE))
        db.commit()
    finally:
        db.close()


_seed()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """每个测试前后清空家长端/登录限流器状态，避免用例间相互影响"""
    ratelimit.parent_limiter.clear()
    ratelimit.login_limiter.clear()
    yield
    ratelimit.parent_limiter.clear()
    ratelimit.login_limiter.clear()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def teacher_headers(client):
    r = client.post("/api/auth/login", data={"username": "teacher1", "password": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def parent_code():
    """有效的测试家长码（勿从本文件 import，会导致 conftest 二次执行）"""
    return PARENT_CODE


@pytest.fixture()
def db_session():
    """测试内直接操作数据库的会话（同一 SQLite 库，用后不提交遗留由用例自行清理）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
