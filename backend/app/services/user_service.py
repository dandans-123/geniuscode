"""会员注册 / 登录业务逻辑。"""
from __future__ import annotations

import secrets
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.security import hash_password, verify_password


def _new_api_key() -> str:
    return "sk-geniuscode-" + secrets.token_hex(24)


def register_user(db: Session, email: str, password: str) -> Tuple[User, ApiKey]:
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if len(password or "") < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="该邮箱已注册")

    user = User(
        email=email,
        password_hash=hash_password(password),
        membership_tier="free",
        credit_balance_cny=settings.FREE_TRIAL_CREDIT_CNY,
    )
    db.add(user)
    db.flush()  # 拿到 user.id

    key = ApiKey(
        key=_new_api_key(),
        name="默认 Key",
        owner_email=email,
        user_id=user.id,
    )
    db.add(key)
    db.commit()
    db.refresh(user)
    db.refresh(key)
    return user, key


def authenticate(db: Session, email: str, password: str) -> User:
    email = (email or "").strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password or "", user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已停用")
    return user


def get_user_api_key(db: Session, user_id: int) -> Optional[ApiKey]:
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user_id, ApiKey.is_active == True)  # noqa: E712
        .order_by(ApiKey.id.asc())
        .first()
    )
