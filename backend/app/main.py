from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine, SessionLocal, Base
from app.models import Provider, Model, RoutingRule, ApiKey, UsageRecord, Budget, KnowledgeBase, Document, KBSubscription
from app.seed.seed_data import seed_database
from app.api.v1.router import router as v1_router
from app.api.admin.router import router as admin_router


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
    title="TaskRouter AI",
    description="Multi-model AI gateway with intelligent routing and usage billing",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(v1_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
