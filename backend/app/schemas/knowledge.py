from __future__ import annotations

from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    name: str
    type: str
    size: int
    chunks: int
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class KBCreate(BaseModel):
    name: str
    industry: str = "general"
    skills: List[str] = []
    embed: str = "bge-m3"


class KBUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    skills: Optional[List[str]] = None
    visibility: Optional[str] = None
    attached: Optional[bool] = None
    publish_desc: Optional[str] = None
    publish_price_mode: Optional[str] = None
    publish_price: Optional[int] = None


class KBResponse(BaseModel):
    id: int
    name: str
    industry: str
    skills: List[str]
    embed: str
    visibility: str
    attached: bool
    publish_desc: Optional[str] = None
    publish_price_mode: str = "free"
    publish_price: int = 0
    docs: List[DocumentResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PublicKBCard(BaseModel):
    id: int
    name: str
    author: str
    verified: bool
    industry: str
    skills: List[str]
    desc: str
    docs: int
    subscribers: int
    rating: float
    price: int
    cover: int
    is_mine: bool = False
    subscribed: bool = False
