from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserResponse, ProfileUpdate
from app.auth import verify_password, get_password_hash, create_access_token, get_current_active_user
from app.config import settings
from app.permissions import is_admin
from app.services import LogService

router = APIRouter(prefix="/api/auth", tags=["认证"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        LogService.log_login(
            db=db,
            user_id=None,
            username=form_data.username,
            ip_address=request.client.host if request and request.client else None,
            user_agent=str(request.headers.get("user-agent")) if request else None,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    LogService.log_login(
        db=db,
        user_id=user.id,
        username=user.username,
        ip_address=request.client.host if request and request.client else None,
        user_agent=str(request.headers.get("user-agent")) if request else None,
        success=True
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建用户（仅管理员）。

    历史版本此接口无认证开放且可指定任意角色（含 admin），存在提权风险；
    日常创建用户请使用「用户管理」页面（POST /api/users，同样仅管理员）。
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以创建用户，请使用「用户管理」页面")

    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        real_name=user_data.real_name,
        role=user_data.role,
        class_id=user_data.class_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/profile", response_model=UserResponse)
def update_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """个人中心：修改本人姓名 / 电话 / 密码。

    - 修改密码必须提供正确的旧密码（old_password）
    - 修改姓名 / 电话时，若任课教师表（teachers）存在同名记录则同步更新，
      保证「任课教师」「班级科目配置」等页面展示一致
    """
    from app.models import Teacher

    changes = []

    # ---- 修改密码（需验证旧密码）----
    if profile_data.new_password is not None:
        if not profile_data.old_password:
            raise HTTPException(status_code=400, detail="请提供旧密码")
        if not verify_password(profile_data.old_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="旧密码错误")
        if len(profile_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="新密码长度不能少于 6 位")
        current_user.hashed_password = get_password_hash(profile_data.new_password)
        changes.append("密码: 已修改")

    # ---- 姓名 / 电话（同步 teachers 表同名记录）----
    old_name = current_user.real_name
    teacher = db.query(Teacher).filter(Teacher.teacher_name == old_name).first()

    if profile_data.real_name is not None and profile_data.real_name != current_user.real_name:
        if not profile_data.real_name.strip():
            raise HTTPException(status_code=400, detail="姓名不能为空")
        changes.append(f"姓名: {current_user.real_name} -> {profile_data.real_name}")
        current_user.real_name = profile_data.real_name.strip()
        if teacher:
            teacher.teacher_name = current_user.real_name

    if profile_data.phone is not None and profile_data.phone != current_user.phone:
        changes.append(f"电话: {current_user.phone or '无'} -> {profile_data.phone}")
        current_user.phone = profile_data.phone
        if teacher:
            teacher.phone = profile_data.phone

    db.commit()
    db.refresh(current_user)

    if changes:
        LogService.log_update(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            target_type="个人中心",
            target_id=current_user.id,
            target_name=f"{current_user.real_name}({current_user.username})",
            changes=", ".join(changes)
        )

    return current_user
