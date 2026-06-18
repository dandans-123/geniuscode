from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.api_key import ApiKey
from app.models.model import Model
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.schemas.auth import AccountOut, AuthOut, LoginIn, PurchaseIn, RegisterIn, SendCodeIn, TopupIn
from app.services.email_service import issue_code, verify_code
from app.services.membership import TIERS, purchase_membership, topup_credit
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


@router.post("/send-code")
def send_code(body: SendCodeIn, db: Session = Depends(get_db)):
    """发送注册邮箱验证码。已配 SMTP → 发邮件;未配 → 开发模式直接回传 code。"""
    code, dev_mode = issue_code(db, body.email)
    if dev_mode:
        return {"sent": True, "dev_mode": True, "code": code}
    return {"sent": True}


@router.post("/register", response_model=AuthOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    verify_code(db, body.email, body.code)  # 邮箱验证码校验,不通过抛 400
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


@router.post("/topup", response_model=AccountOut)
def topup(
    body: TopupIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topup_credit(db, user, body.amount_cny)
    return _account(db, user)


@router.get("/usage")
def usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户的用量汇总：总调用 / 总 token / 总花费(¥) + 按模型 + 最近 10 条。"""
    key_ids = [k.id for k in db.query(ApiKey).filter(ApiKey.user_id == user.id).all()]
    if not key_ids:
        return {"total_calls": 0, "total_tokens": 0, "total_cost_cny": 0.0, "by_model": [], "recent": []}

    calls, tokens, cost = (
        db.query(
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
        )
        .filter(UsageRecord.api_key_id.in_(key_ids))
        .one()
    )

    name_map = {m.id: m.name for m in db.query(Model).all()}

    by_model_rows = (
        db.query(
            UsageRecord.model_id,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
        )
        .filter(UsageRecord.api_key_id.in_(key_ids))
        .group_by(UsageRecord.model_id)
        .all()
    )
    by_model = [
        {"model": name_map.get(mid, str(mid)), "calls": c, "cost_cny": round(co, 6)}
        for mid, c, co in sorted(by_model_rows, key=lambda r: r[2], reverse=True)
    ]

    recent_rows = (
        db.query(UsageRecord)
        .filter(UsageRecord.api_key_id.in_(key_ids))
        .order_by(UsageRecord.created_at.desc())
        .limit(10)
        .all()
    )
    recent = [
        {
            "model": name_map.get(r.model_id, str(r.model_id)),
            "tokens": r.total_tokens,
            "cost_cny": round(r.cost_usd, 6),
            "status": r.status,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_rows
    ]

    return {
        "total_calls": calls,
        "total_tokens": int(tokens),
        "total_cost_cny": round(cost, 4),
        "by_model": by_model,
        "recent": recent,
    }
