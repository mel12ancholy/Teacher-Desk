from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Student, SeatingChart
from app.schemas import SeatingSaveRequest, SeatingChartResponse, SeatingStudent
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids

router = APIRouter(prefix="/api/seating", tags=["换座位"])

MIN_ROWS, MAX_ROWS = 4, 12
MIN_COLUMNS, MAX_COLUMNS = 4, 16


def _validate_class_access(class_id: int, current_user: User, db: Session):
    """校验班级存在且当前用户有权限访问"""
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该班级")
    return class_ids


def _parse_date(date_str: Optional[str]) -> date:
    """解析 YYYY-MM-DD 日期参数"""
    if not date_str:
        return date.today()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")


@router.get("", response_model=SeatingChartResponse)
def get_seating_chart(
    class_id: int,
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询指定日期（默认今天）的座位表，仅限有权限的班级"""
    _validate_class_access(class_id, current_user, db)
    target_date = _parse_date(date)

    records = db.query(SeatingChart).filter(
        SeatingChart.class_id == class_id,
        SeatingChart.created_date == target_date
    ).all()

    if not records:
        raise HTTPException(status_code=404, detail="该日期暂无座位表数据")

    return SeatingChartResponse(
        class_id=class_id,
        date=target_date.isoformat(),
        row_count=records[0].row_count,
        column_count=records[0].column_count,
        students=[
            SeatingStudent(
                student_id=r.student_id,
                student_name=r.student_name,
                seat_row=r.seat_row,
                seat_column=r.seat_column
            )
            for r in records
        ]
    )


@router.post("/save", response_model=SeatingChartResponse)
def save_seating_chart(
    data: SeatingSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """保存当天座位表（同班同天仅一份：先删后插，历史日期不受影响）"""
    _validate_class_access(data.class_id, current_user, db)

    if not (MIN_ROWS <= data.row_count <= MAX_ROWS):
        raise HTTPException(status_code=400, detail=f"行数必须在 {MIN_ROWS} ~ {MAX_ROWS} 之间")
    if not (MIN_COLUMNS <= data.column_count <= MAX_COLUMNS):
        raise HTTPException(status_code=400, detail=f"列数必须在 {MIN_COLUMNS} ~ {MAX_COLUMNS} 之间")

    # 校验学生归属与座位坐标
    seen_students = set()      # 防止同一学生重复
    seen_names = set()         # 防止 Excel 姓名重复
    seen_seats = set()         # 防止座位坐标冲突
    for s in data.students:
        name = (s.student_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="学生姓名不能为空")
        if s.student_id is not None:
            student = db.query(Student).filter(Student.id == s.student_id).first()
            if not student:
                raise HTTPException(status_code=400, detail=f"学生 {name} 不存在")
            if student.class_id != data.class_id:
                raise HTTPException(status_code=403, detail=f"学生 {name} 不属于该班级")
            if s.student_id in seen_students:
                raise HTTPException(status_code=400, detail=f"学生 {name} 重复出现")
            seen_students.add(s.student_id)
            if name != student.name:
                name = student.name  # 以学生主数据为准
        else:
            # Excel 导入的学生仅按姓名去重
            if name in seen_names:
                raise HTTPException(status_code=400, detail=f"学生姓名 {name} 重复出现")
            seen_names.add(name)

        if (s.seat_row is None) != (s.seat_column is None):
            raise HTTPException(status_code=400, detail=f"学生 {name} 的座位行列必须同时为空或同时有值")
        if s.seat_row is not None:
            if not (1 <= s.seat_row <= data.row_count) or not (1 <= s.seat_column <= data.column_count):
                raise HTTPException(status_code=400, detail=f"学生 {name} 的座位坐标超出范围")
            seat = (s.seat_row, s.seat_column)
            if seat in seen_seats:
                raise HTTPException(status_code=400, detail=f"座位 {s.seat_row}-{s.seat_column} 被多个学生占用")
            seen_seats.add(seat)

    today = date.today()
    try:
        # 同班同天先删后插，保证唯一一份座位表
        db.query(SeatingChart).filter(
            SeatingChart.class_id == data.class_id,
            SeatingChart.created_date == today
        ).delete(synchronize_session=False)

        for s in data.students:
            db.add(SeatingChart(
                class_id=data.class_id,
                user_id=current_user.id,
                student_id=s.student_id,
                student_name=(s.student_name or "").strip(),
                row_count=data.row_count,
                column_count=data.column_count,
                seat_row=s.seat_row,
                seat_column=s.seat_column,
                created_date=today
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存座位表失败: {str(e)}")

    return SeatingChartResponse(
        class_id=data.class_id,
        date=today.isoformat(),
        row_count=data.row_count,
        column_count=data.column_count,
        students=data.students
    )


@router.get("/dates")
def get_seating_dates(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询历史座次日期（去重、降序），仅限有权限的班级"""
    _validate_class_access(class_id, current_user, db)

    dates = db.query(SeatingChart.created_date).filter(
        SeatingChart.class_id == class_id
    ).distinct().order_by(SeatingChart.created_date.desc()).all()

    return [d[0].isoformat() for d in dates]


@router.delete("")
def clear_seating_chart(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """清除当天座位表（仅允许清除当天数据，历史日期由服务端强制保护）"""
    _validate_class_access(class_id, current_user, db)
    today = date.today()

    deleted = db.query(SeatingChart).filter(
        SeatingChart.class_id == class_id,
        SeatingChart.created_date == today
    ).delete(synchronize_session=False)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清除座位表失败: {str(e)}")

    return {"message": "清除成功", "deleted": deleted}
