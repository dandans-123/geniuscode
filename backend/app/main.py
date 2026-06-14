from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, SessionLocal, Base
from app.models import Provider, Model, RoutingRule, ApiKey, UsageRecord, Budget, KnowledgeBase, Document, KBSubscription, User
from app.seed.seed_data import seed_database
from app.api.v1.router import router as v1_router
from app.api.admin.router import router as admin_router
from app.api.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Seed data
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="GeniusCode AI",
    description="多模型 AI 网关：统一 OpenAI 兼容接口，智能路由 + 按量计费，上游中转 aicodewith",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(v1_router)
app.include_router(admin_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
