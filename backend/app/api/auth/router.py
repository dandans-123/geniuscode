from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import AccountOut, AuthOut, LoginIn, PurchaseIn, RegisterIn
from app.services.membership import TIERS, purchase_membership
from app.services.security import create_token
from app.services.user_service import authenticate, get_user_api_key, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _account(db: Session, user: User) -> AccountOut:
    key = get_user_api_key(db, user.id)
    return AccountOut(
        email=user.email,
        membership_tier=user.membership_tier,
        credit_balance_cny=round(user.credit_balance_cny, 2),
        membership_expires_at=user.membership_expires_at.isoformat() if user.membership_expires_at else None,
        api_key=key.key if key else None,
    )


@router.post("/register", response_model=AuthOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    user, _ = register_user(db, body.email, body.password)
    return AuthOut(access_token=create_token(user.id), account=_account(db, user))


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = authenticate(db, body.email, body.password)
    return AuthOut(access_token=create_token(user.id), account=_account(db, user))


@router.get("/account", response_model=AccountOut)
def account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _account(db, user)


@router.get("/membership/tiers")
def membership_tiers():
    return {"tiers": [{"id": k, **v} for k, v in TIERS.items()]}


@router.post("/membership/purchase", response_model=AccountOut)
def membership_purchase(
    body: PurchaseIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purchase_membership(db, user, body.tier)
    return _account(db, user)
