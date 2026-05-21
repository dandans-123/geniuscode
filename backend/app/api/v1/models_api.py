from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_api_key
from app.models.model import Model
from app.models.api_key import ApiKey

router = APIRouter()


@router.get("/models")
def list_models(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    models = db.query(Model).all()
    return {
        "object": "list",
        "data": [
            {
                "id": m.name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "modelmux",
                "permission": [],
                "root": m.name,
                "parent": None,
            }
            for m in models
        ],
    }
