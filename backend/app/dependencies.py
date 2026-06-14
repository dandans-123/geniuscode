from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.auth_service import verify_api_key, verify_admin_key
from app.services.security import decode_token


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_api_key(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> ApiKey:
    return verify_api_key(authorization, db)


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """会员控制台鉴权：解析 Authorization: Bearer <登录 token>（区别于 /v1 的 API key）。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少登录凭证")
    user_id = decode_token(authorization[7:])
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已过期或无效，请重新登录")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="账户不存在或已停用")
    return user
