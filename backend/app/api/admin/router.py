from __future__ import annotations

from fastapi import APIRouter

from app.api.admin.health import router as health_router
from app.api.admin.providers import router as providers_router
from app.api.admin.models_admin import router as models_router
from app.api.admin.routing_rules import router as routing_rules_router
from app.api.admin.api_keys import router as api_keys_router
from app.api.admin.usage import router as usage_router
from app.api.admin.budgets import router as budgets_router

router = APIRouter(prefix="/admin")
router.include_router(health_router)
router.include_router(providers_router)
router.include_router(models_router)
router.include_router(routing_rules_router)
router.include_router(api_keys_router)
router.include_router(usage_router)
router.include_router(budgets_router)
