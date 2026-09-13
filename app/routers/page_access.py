from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, PageAccessConfig
from app.schemas import PageAccessBatchUpdate, PageAccessResponse, MyPageAccessResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/page-access", tags=["页面访问配置"])

VALID_ROLES = {"admin", "class_teacher", "teacher"}


def _is_admin(user: User) -> bool:
    return (user.role or "").lower() == "admin"


@router.get("/my", response_model=MyPageAccessResponse)
def get_my_page_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询当前用户角色被隐藏的页面列表（无记录 = 默认全部可见）"""
    configs = db.query(PageAccessConfig).filter(
        PageAccessConfig.role == current_user.role,
        PageAccessConfig.is_visible == False  # noqa: E712
    ).all()
    return MyPageAccessResponse(
        role=current_user.role,
        hidden_pages=[c.page_path for c in configs]
    )


@router.get("", response_model=List[PageAccessResponse])
def get_all_page_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """查询全部页面访问配置（仅管理员）"""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可管理页面访问配置")
    return db.query(PageAccessConfig).order_by(PageAccessConfig.role, PageAccessConfig.page_path).all()


@router.put("", response_model=List[PageAccessResponse])
def batch_update_page_access(
    data: PageAccessBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """批量更新页面访问配置（仅管理员）

    幂等 upsert：存在则更新，不存在则新增。
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可管理页面访问配置")

    for item in data.configs:
        if item.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"无效角色: {item.role}")
        if not item.page_path or not item.page_path.startswith("/"):
            raise HTTPException(status_code=400, detail=f"无效页面路径: {item.page_path}")

    try:
        for item in data.configs:
            existing = db.query(PageAccessConfig).filter(
                PageAccessConfig.role == item.role,
                PageAccessConfig.page_path == item.page_path
            ).first()
            if existing:
                existing.is_visible = item.is_visible
            else:
                db.add(PageAccessConfig(
                    role=item.role,
                    page_path=item.page_path,
                    is_visible=item.is_visible
                ))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")

    return db.query(PageAccessConfig).order_by(PageAccessConfig.role, PageAccessConfig.page_path).all()
