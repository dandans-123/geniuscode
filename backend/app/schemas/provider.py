from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class ProviderBase(BaseModel):
    name: str
    base_url: str
    api_key_env_var: Optional[str] = None
    is_enabled: bool = True


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key_env_var: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_healthy: Optional[bool] = None


class ProviderResponse(ProviderBase):
    id: int
    is_healthy: bool

    class Config:
        from_attributes = True
