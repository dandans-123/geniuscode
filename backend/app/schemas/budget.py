from __future__ import annotations

from typing import Optional
from datetime import date
from pydantic import BaseModel


class BudgetBase(BaseModel):
    api_key_id: int
    monthly_limit_usd: float = 100.0
    daily_limit_usd: float = 10.0
    per_request_limit_usd: float = 1.0


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    monthly_limit_usd: Optional[float] = None
    daily_limit_usd: Optional[float] = None
    per_request_limit_usd: Optional[float] = None


class BudgetResponse(BudgetBase):
    id: int
    current_monthly_usage_usd: float
    current_daily_usage_usd: float
    last_monthly_reset: Optional[date] = None
    last_daily_reset: Optional[date] = None

    class Config:
        from_attributes = True
