from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.auth_service import verify_admin_key
from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/providers", response_model=list[ProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    return db.query(Provider).all()


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers", response_model=ProviderResponse)
def create_provider(data: ProviderCreate, db: Session = Depends(get_db)):
    provider = Provider(**data.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, data: ProviderUpdate, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(provider)
    db.commit()
    return {"detail": "deleted"}
