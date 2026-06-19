from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RegisterIn(BaseModel):
    email: str
    password: str
    code: str = ""  # 邮箱验证码


class SendCodeIn(BaseModel):
    email: str


class LoginIn(BaseModel):
    email: str
    password: str


class PurchaseIn(BaseModel):
    tier: str  # starter / pro / ultimate


class TopupIn(BaseModel):
    amount_cny: float


class AccountOut(BaseModel):
    email: str
    membership_tier: str
    credit_balance_cny: float
    membership_expires_at: Optional[str] = None
    api_key: Optional[str] = None
    is_admin: bool = False


class GroupIn(BaseModel):
    name: str
    description: str = ""
    platform: str = "aicodewith"
    rate_multiplier: float = 1.0
    rpm: int = 0
    visibility: str = "public"
    billing_type: str = "standard"


class MyGroupIn(BaseModel):
    """用户自建分组(无费率,费率由平台统一)。"""
    name: str
    description: str = ""
    rpm: int = 0
    models: list[str] = []


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: AccountOut
