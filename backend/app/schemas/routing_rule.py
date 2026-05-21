from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class RoutingRuleBase(BaseModel):
    industry: str
    task_type: str
    primary_model_id: int
    fallback_model_id: int
    specialist_model_id: int
    quality_score: float = 0.0
    speed_score: float = 0.0
    cost_score: float = 0.0
    description: str = ""
    reason: str = ""
    estimated_cost: str = ""


class RoutingRuleCreate(RoutingRuleBase):
    pass


class RoutingRuleUpdate(BaseModel):
    primary_model_id: Optional[int] = None
    fallback_model_id: Optional[int] = None
    specialist_model_id: Optional[int] = None
    quality_score: Optional[float] = None
    speed_score: Optional[float] = None
    cost_score: Optional[float] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    estimated_cost: Optional[str] = None


class RoutingRuleResponse(RoutingRuleBase):
    id: int

    class Config:
        from_attributes = True
