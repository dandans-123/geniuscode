"""会员套餐 + ¥额度计费。

套餐对齐 aicodewith：一次开通，价格 = 等值额度入账，额度 12 个月有效。
支付为桩——`purchase_membership` 默认视为已支付成功；接入真实支付
（支付宝 / 微信 / Stripe）时，应在支付确认回调里再调用本函数入账。
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.models.user import User


# id -> 套餐配置。price_cny 即开通价；credit_cny 为到账等值额度。
TIERS = {
    "starter": {"name": "Starter", "price_cny": 399.0, "credit_cny": 399.0, "rate_limit_rpm": 60, "concurrency": 2},
    "pro": {"name": "Pro", "price_cny": 699.0, "credit_cny": 699.0, "rate_limit_rpm": 120, "concurrency": 5},
    "ultimate": {"name": "Ultimate", "price_cny": 1799.0, "credit_cny": 1799.0, "rate_limit_rpm": 300, "concurrency": 20},
}

CREDIT_VALIDITY_DAYS = 365


def purchase_membership(db: Session, user: User, tier: str) -> User:
    """开通 / 续费会员套餐（桩支付：默认支付成功）。

    入账等值额度、置会员等级、把额度有效期顺延 12 个月。
    """
    cfg = TIERS.get(tier)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"未知套餐: {tier}")

    # TODO(支付): 接入真实支付后，仅在收到「支付成功」回调时执行下面的入账。
    user.membership_tier = tier
    user.credit_balance_cny = round(user.credit_balance_cny + cfg["credit_cny"], 2)
    user.membership_expires_at = date.today() + timedelta(days=CREDIT_VALIDITY_DAYS)
    db.commit()
    db.refresh(user)
    return user


def check_user_credit(db: Session, api_key: ApiKey) -> None:
    """/v1 调用前置校验：绑定会员的余额是否充足。

    平台 dev key（user_id 为 None）不受限，便于内部调试。
    """
    if api_key.user_id is None:
        return
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        return
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已停用")
    if user.membership_expires_at and user.membership_expires_at < date.today():
        raise HTTPException(status_code=402, detail="额度已过期，请续费会员")
    if user.credit_balance_cny <= 0:
        raise HTTPException(status_code=402, detail="额度不足，请开通 / 续费会员")


def deduct_user_credit(db: Session, api_key_id: int, cost_cny: float) -> None:
    """请求成功后从绑定会员余额扣除实际成本（¥）。dev key 不扣。"""
    if cost_cny <= 0:
        return
    ak = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not ak or ak.user_id is None:
        return
    user = db.query(User).filter(User.id == ak.user_id).first()
    if not user:
        return
    user.credit_balance_cny = round(user.credit_balance_cny - cost_cny, 6)
    db.commit()
