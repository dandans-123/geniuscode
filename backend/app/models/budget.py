from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import Integer, Float, ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), unique=True, nullable=False)
    monthly_limit_usd: Mapped[float] = mapped_column(Float, default=100.0)
    daily_limit_usd: Mapped[float] = mapped_column(Float, default=10.0)
    per_request_limit_usd: Mapped[float] = mapped_column(Float, default=1.0)
    current_monthly_usage_usd: Mapped[float] = mapped_column(Float, default=0.0)
    current_daily_usage_usd: Mapped[float] = mapped_column(Float, default=0.0)
    last_monthly_reset: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_daily_reset: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
