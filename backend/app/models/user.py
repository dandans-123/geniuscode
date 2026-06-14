from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Boolean, Float, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """会员用户。一个 User 拥有若干 ApiKey；额度以 ¥ 计（credit_balance_cny）。

    membership_tier: free / starter / pro / ultimate
    会员套餐为预付制——购买即按等值额度入账，membership_expires_at 为额度有效期。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    membership_tier: Mapped[str] = mapped_column(String(20), default="free")
    credit_balance_cny: Mapped[float] = mapped_column(Float, default=0.0)
    membership_expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
