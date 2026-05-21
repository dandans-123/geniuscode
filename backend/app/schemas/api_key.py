from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ApiKeyBase(BaseModel):
    name: str
    owner_email: Optional[str] = None
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000


class ApiKeyCreate(ApiKeyBase):
    key: Optional[str] = None
    expires_at: Optional[datetime] = None


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    owner_email: Optional[str] = None
    is_active: Optional[bool] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    expires_at: Optional[datetime] = None


class ApiKeyResponse(ApiKeyBase):
    id: int
    key: str
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
