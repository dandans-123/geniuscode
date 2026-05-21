from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class UsageRecordResponse(BaseModel):
    id: int
    request_id: str
    api_key_id: int
    model_id: int
    provider_id: int
    routing_strategy: str
    industry: str
    task_type: str
    was_fallback: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    status: str
    error_message: str
    created_at: datetime

    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    error_rate: float
