from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Integer, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Group(Base):
    """API 密钥分组 / 服务套餐(运营配置,对标 Sub2API 的分组管理)。

    rate_multiplier: 计费倍率(1.0=原价, 1.5/2.0=加价, 0.8=补贴)。
    visibility: public(公开,所有用户可见) / private(专属,指定用户)。
    billing_type: standard(按余额) / subscription(订阅配额)。
    注:本期为管理配置 + 展示;在计费/路由中的强制生效为二期。
    """

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    platform: Mapped[str] = mapped_column(String(30), default="aicodewith")
    rate_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    rpm: Mapped[int] = mapped_column(Integer, default=0)  # 0 = 不限
    visibility: Mapped[str] = mapped_column(String(10), default="public")
    billing_type: Mapped[str] = mapped_column(String(20), default="standard")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
