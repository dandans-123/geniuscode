from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class PurchaseIn(BaseModel):
    tier: str  # starter / pro / ultimate


class AccountOut(BaseModel):
    email: str
    membership_tier: str
    credit_balance_cny: float
    membership_expires_at: Optional[str] = None
    api_key: Optional[str] = None


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: AccountOut
