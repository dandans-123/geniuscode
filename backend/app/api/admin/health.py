from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.dependencies import get_db
from app.models.provider import Provider
from app.models.model import Model
from app.models.usage_record import UsageRecord

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    # DB connectivity
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # Provider health
    providers = db.query(Provider).all()
    healthy_providers = sum(1 for p in providers if p.is_healthy)

    # Stats
    model_count = db.query(Model).count()
    usage_count = db.query(UsageRecord).count()

    return {
        "status": "ok",
        "database": db_status,
        "providers": {"total": len(providers), "healthy": healthy_providers},
        "models": model_count,
        "total_requests": usage_count,
    }
