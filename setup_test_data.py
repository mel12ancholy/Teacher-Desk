"""创建换座位/超行分功能自测所需的测试数据：班级、班主任、学生"""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User, Class, Student, UserRole
from app.auth import get_password_hash

db = SessionLocal()

# 班级
c1 = db.query(Class).filter(Class.name == '高一(1)班').first()
if not c1:
    c1 = Class(name='高一(1)班', grade=1)
    db.add(c1)
    db.flush()

c2 = db.query(Class).filter(Class.name == '高一(2)班').first()
if not c2:
    c2 = Class(name='高一(2)班', grade=1)
    db.add(c2)
    db.flush()

# 班主任
t1 = db.query(User).filter(User.username == 'teacher1').first()
if not t1:
    t1 = User(
        username='teacher1',
        hashed_password=get_password_hash('123456'),
        real_name='张老师',
        role=UserRole.CLASS_TEACHER,
        class_id=c1.id
    )
    db.add(t1)
    db.flush()

t2 = db.query(User).filter(User.username == 'teacher2').first()
if not t2:
    t2 = User(
        username='teacher2',
        hashed_password=get_password_hash('123456'),
        real_name='李老师',
        role=UserRole.CLASS_TEACHER,
        class_id=c2.id
    )
    db.add(t2)
    db.flush()

# 学生
names = ['张三', '李四', '王五', '赵六', '王强', '李明', '陈晓', '刘洋', '周杰', '吴霞']
for i, name in enumerate(names, 1):
    no = f'S{i:03d}'
    exists = db.query(Student).filter(Student.class_id == c1.id, Student.student_no == no).first()
    if not exists:
        db.add(Student(name=name, student_no=no, class_id=c1.id, gender='male'))

for i, name in enumerate(['孙八', '钱九'], 1):
    no = f'T{i:03d}'
    exists = db.query(Student).filter(Student.class_id == c2.id, Student.student_no == no).first()
    if not exists:
        db.add(Student(name=name, student_no=no, class_id=c2.id, gender='female'))

db.commit()
print('班级:', [(c.id, c.name) for c in [c1, c2]])
print('teacher1:', t1.id, t1.username, 'class_id=', t1.class_id)
print('teacher2:', t2.id, t2.username, 'class_id=', t2.class_id)
print('c1 学生:', [(s.id, s.name) for s in db.query(Student).filter(Student.class_id == c1.id).all()])
print('c2 学生:', [(s.id, s.name) for s in db.query(Student).filter(Student.class_id == c2.id).all()])
db.close()
