from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(200), nullable=True)
    # 归属会员用户；平台 dev key 为 None（不计费、不限额）。
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60)
    rate_limit_tpm: Mapped[int] = mapped_column(Integer, default=100000)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
