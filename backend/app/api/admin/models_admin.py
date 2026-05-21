from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.auth_service import verify_admin_key
from app.models.model import Model
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/models", response_model=list[ModelResponse])
def list_models(db: Session = Depends(get_db)):
    return db.query(Model).all()


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/models", response_model=ModelResponse)
def create_model(data: ModelCreate, db: Session = Depends(get_db)):
    model = Model(**data.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.put("/models/{model_id}", response_model=ModelResponse)
def update_model(model_id: int, data: ModelUpdate, db: Session = Depends(get_db)):
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    db.commit()
    db.refresh(model)
    return model


@router.delete("/models/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(model)
    db.commit()
    return {"detail": "deleted"}
