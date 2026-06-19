from __future__ import annotations

from datetime import datetime

from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Group(Base):
    """分组。两类:
    - 平台分组(user_id 为 None):管理员运营配置,含费率倍数/可见性/计费类型。
    - 用户分组(user_id 非空):用户自建,用于组织自己的 key + 自管限速(RPM)+ 模型白名单;
      费率由平台统一决定,用户分组的 rate_multiplier 恒为 1.0、不开放。
    注:计费/路由中的强制生效为二期。
    """

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    platform: Mapped[str] = mapped_column(String(30), default="aicodewith")
    rate_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    rpm: Mapped[int] = mapped_column(Integer, default=0)  # 0 = 不限
    models: Mapped[str] = mapped_column(Text, default="[]")  # JSON 模型白名单,空=全部
    visibility: Mapped[str] = mapped_column(String(10), default="public")
    billing_type: Mapped[str] = mapped_column(String(20), default="standard")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
