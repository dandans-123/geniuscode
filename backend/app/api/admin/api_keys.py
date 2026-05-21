from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.auth_service import verify_admin_key
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(db: Session = Depends(get_db)):
    return db.query(ApiKey).all()


@router.get("/api-keys/{key_id}", response_model=ApiKeyResponse)
def get_api_key(key_id: int, db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(data: ApiKeyCreate, db: Session = Depends(get_db)):
    key = data.key or f"sk-modelmux-{secrets.token_hex(24)}"
    api_key = ApiKey(
        key=key,
        name=data.name,
        owner_email=data.owner_email,
        rate_limit_rpm=data.rate_limit_rpm,
        rate_limit_tpm=data.rate_limit_tpm,
        expires_at=data.expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


@router.put("/api-keys/{key_id}", response_model=ApiKeyResponse)
def update_api_key(key_id: int, data: ApiKeyUpdate, db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(api_key, key, value)
    db.commit()
    db.refresh(api_key)
    return api_key


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int, db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(api_key)
    db.commit()
    return {"detail": "deleted"}
