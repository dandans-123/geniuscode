from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.api_key import ApiKey
from app.services.auth_service import verify_api_key, verify_admin_key


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_api_key(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> ApiKey:
    return verify_api_key(authorization, db)
