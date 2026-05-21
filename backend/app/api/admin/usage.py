from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_db
from app.services.auth_service import verify_admin_key
from app.models.usage_record import UsageRecord
from app.schemas.usage import UsageRecordResponse, UsageSummary

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/usage/summary", response_model=UsageSummary)
def usage_summary(db: Session = Depends(get_db)):
    total_requests = db.query(UsageRecord).count()
    if total_requests == 0:
        return UsageSummary(
            total_requests=0, total_tokens=0, total_cost_usd=0.0, avg_latency_ms=0.0, error_rate=0.0
        )

    total_tokens = db.query(func.sum(UsageRecord.total_tokens)).scalar() or 0
    total_cost = db.query(func.sum(UsageRecord.cost_usd)).scalar() or 0.0
    avg_latency = db.query(func.avg(UsageRecord.latency_ms)).scalar() or 0.0
    error_count = db.query(UsageRecord).filter(UsageRecord.status != "success").count()

    return UsageSummary(
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        avg_latency_ms=round(avg_latency, 1),
        error_rate=round(error_count / total_requests, 4) if total_requests > 0 else 0.0,
    )


@router.get("/usage/recent", response_model=list[UsageRecordResponse])
def recent_usage(limit: int = Query(default=20, le=100), db: Session = Depends(get_db)):
    return (
        db.query(UsageRecord)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/usage/by-model")
def usage_by_model(db: Session = Depends(get_db)):
    results = (
        db.query(
            UsageRecord.model_id,
            func.count(UsageRecord.id).label("requests"),
            func.sum(UsageRecord.total_tokens).label("tokens"),
            func.sum(UsageRecord.cost_usd).label("cost"),
        )
        .group_by(UsageRecord.model_id)
        .all()
    )
    return [
        {"model_id": r[0], "requests": r[1], "tokens": r[2] or 0, "cost": round(r[3] or 0, 6)}
        for r in results
    ]


@router.get("/usage/by-day")
def usage_by_day(db: Session = Depends(get_db)):
    results = (
        db.query(
            func.date(UsageRecord.created_at).label("day"),
            func.count(UsageRecord.id).label("requests"),
            func.sum(UsageRecord.cost_usd).label("cost"),
        )
        .group_by(func.date(UsageRecord.created_at))
        .order_by(func.date(UsageRecord.created_at).desc())
        .limit(30)
        .all()
    )
    return [
        {"day": str(r[0]), "requests": r[1], "cost": round(r[2] or 0, 6)}
        for r in results
    ]
