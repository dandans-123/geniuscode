from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.messages import router as messages_router
from app.api.v1.models_api import router as models_router
from app.api.v1.knowledge import router as knowledge_router

router = APIRouter(prefix="/v1")
router.include_router(chat_router)
router.include_router(messages_router)
router.include_router(models_router)
router.include_router(knowledge_router)
