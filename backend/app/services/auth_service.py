from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, Header
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.config import settings


def verify_api_key(authorization: str, db: Session) -> ApiKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]  # strip "Bearer "
    api_key = db.query(ApiKey).filter(ApiKey.key == token).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not api_key.is_active:
        raise HTTPException(status_code=401, detail="API key is inactive")
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key has expired")

    api_key.last_used_at = datetime.utcnow()
    db.commit()
    return api_key


def verify_admin_key(x_admin_key: str = Header(None)):
    if not x_admin_key or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
