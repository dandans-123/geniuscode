from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.model import Model


def calculate_cost(model: Model, prompt_tokens: int, completion_tokens: int) -> float:
    input_cost = (prompt_tokens / 1000) * model.cost_per_1k_input
    output_cost = (completion_tokens / 1000) * model.cost_per_1k_output
    return round(input_cost + output_cost, 6)


def check_budget(db: Session, api_key_id: int, estimated_cost: float = 0.0):
    budget = db.query(Budget).filter(Budget.api_key_id == api_key_id).first()
    if not budget:
        return  # No budget means no limits

    today = date.today()

    # Lazy daily reset
    if budget.last_daily_reset != today:
        budget.current_daily_usage_usd = 0.0
        budget.last_daily_reset = today

    # Lazy monthly reset
    if budget.last_monthly_reset is None or budget.last_monthly_reset.month != today.month or budget.last_monthly_reset.year != today.year:
        budget.current_monthly_usage_usd = 0.0
        budget.last_monthly_reset = today

    db.commit()

    # Per-request check
    if estimated_cost > budget.per_request_limit_usd:
        raise HTTPException(
            status_code=429,
            detail=f"Request cost ${estimated_cost:.4f} exceeds per-request limit ${budget.per_request_limit_usd:.2f}",
        )

    # Daily check
    if budget.current_daily_usage_usd + estimated_cost > budget.daily_limit_usd:
        raise HTTPException(
            status_code=429,
            detail=f"Daily budget limit ${budget.daily_limit_usd:.2f} would be exceeded",
        )

    # Monthly check
    if budget.current_monthly_usage_usd + estimated_cost > budget.monthly_limit_usd:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly budget limit ${budget.monthly_limit_usd:.2f} would be exceeded",
        )


def record_usage_cost(db: Session, api_key_id: int, cost: float):
    budget = db.query(Budget).filter(Budget.api_key_id == api_key_id).first()
    if not budget:
        return
    budget.current_daily_usage_usd += cost
    budget.current_monthly_usage_usd += cost
    db.commit()
