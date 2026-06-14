from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.seed.seed_data import seed_database
from app.services.routing_engine import route_request, try_fallback
from app.services.circuit_breaker import circuit_breaker


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_database(session)
    yield session
    session.close()


def test_cost_optimized_strategy(db):
    decision = route_request(db, strategy="cost_optimized")
    assert decision.strategy_used == "cost_optimized"
    assert decision.model_id > 0


def test_quality_optimized_strategy(db):
    decision = route_request(db, strategy="quality_optimized")
    assert decision.strategy_used == "quality_optimized"
    assert decision.model_id > 0


def test_balanced_strategy(db):
    decision = route_request(db, strategy="balanced")
    assert decision.strategy_used == "balanced"
    assert decision.model_id > 0


def test_latency_optimized_strategy(db):
    decision = route_request(db, strategy="latency_optimized")
    assert decision.strategy_used == "latency_optimized"
    assert decision.model_id > 0


def test_model_override(db):
    decision = route_request(db, model_override="deepseek-v3.2")
    assert decision.model_name == "deepseek-v3.2"
    assert decision.strategy_used == "override"


def test_industry_task_routing(db):
    decision = route_request(db, industry="default", task_type="chat")
    assert "rule:default/chat" in decision.strategy_used
    assert decision.model_id > 0
    assert len(decision.fallback_chain) > 0


def test_fallback_chain(db):
    decision = route_request(db, industry="default", task_type="code_generation")
    assert len(decision.fallback_chain) > 0

    fallback = try_fallback(db, decision.fallback_chain)
    assert fallback is not None
    assert fallback.was_fallback is True


def test_circuit_breaker_trip(db):
    decision = route_request(db, model_override="deepseek-v3.2")
    provider_id = decision.provider_id

    # Trip the circuit breaker
    for _ in range(5):
        circuit_breaker.record_failure(provider_id)

    assert not circuit_breaker.is_available(provider_id)

    # Routing should still work (picks another model)
    decision2 = route_request(db, strategy="balanced")
    assert decision2.model_id > 0

    # Reset for other tests
    circuit_breaker.record_success(provider_id)
