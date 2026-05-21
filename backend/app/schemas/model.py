from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ModelBase(BaseModel):
    name: str
    provider_id: int
    quality_score: float = 0.5
    speed_score: float = 0.5
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency_ms: int = 1000
    tokens_per_second: int = 50
    max_context_length: int = 4096
    capabilities: str = "[]"
    is_mock: bool = True


class ModelCreate(ModelBase):
    pass


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    provider_id: Optional[int] = None
    quality_score: Optional[float] = None
    speed_score: Optional[float] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None
    avg_latency_ms: Optional[int] = None
    tokens_per_second: Optional[int] = None
    max_context_length: Optional[int] = None
    capabilities: Optional[str] = None
    is_mock: Optional[bool] = None


class ModelResponse(ModelBase):
    id: int

    class Config:
        from_attributes = True
