from __future__ import annotations

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.seed.seed_data import seed_database
from app.models.model import Model
from app.models.budget import Budget
from app.services.billing_engine import calculate_cost, check_budget, record_usage_cost


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


def test_calculate_cost(db):
    model = db.query(Model).filter(Model.name == "gpt-4o").first()
    cost = calculate_cost(model, prompt_tokens=1000, completion_tokens=500)
    expected = (1000 / 1000) * model.cost_per_1k_input + (500 / 1000) * model.cost_per_1k_output
    assert abs(cost - expected) < 0.000001


def test_calculate_cost_zero_tokens(db):
    model = db.query(Model).filter(Model.name == "gpt-4o").first()
    cost = calculate_cost(model, prompt_tokens=0, completion_tokens=0)
    assert cost == 0.0


def test_check_budget_within_limits(db):
    # Should not raise
    check_budget(db, api_key_id=1, estimated_cost=0.001)


def test_check_budget_per_request_exceeded(db):
    with pytest.raises(HTTPException) as exc_info:
        check_budget(db, api_key_id=1, estimated_cost=5.0)
    assert exc_info.value.status_code == 429
    assert "per-request limit" in exc_info.value.detail


def test_check_budget_daily_exceeded(db):
    budget = db.query(Budget).filter(Budget.api_key_id == 1).first()
    budget.current_daily_usage_usd = 9.99
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        check_budget(db, api_key_id=1, estimated_cost=0.02)
    assert exc_info.value.status_code == 429
    assert "Daily budget" in exc_info.value.detail


def test_check_budget_monthly_exceeded(db):
    budget = db.query(Budget).filter(Budget.api_key_id == 1).first()
    budget.current_monthly_usage_usd = 99.99
    db.commit()
    with pytest.raises(HTTPException) as exc_info:
        check_budget(db, api_key_id=1, estimated_cost=0.02)
    assert exc_info.value.status_code == 429
    assert "Monthly budget" in exc_info.value.detail


def test_record_usage_cost(db):
    budget = db.query(Budget).filter(Budget.api_key_id == 1).first()
    initial_daily = budget.current_daily_usage_usd
    initial_monthly = budget.current_monthly_usage_usd

    record_usage_cost(db, api_key_id=1, cost=0.05)

    db.refresh(budget)
    assert budget.current_daily_usage_usd == initial_daily + 0.05
    assert budget.current_monthly_usage_usd == initial_monthly + 0.05


def test_daily_reset(db):
    budget = db.query(Budget).filter(Budget.api_key_id == 1).first()
    budget.current_daily_usage_usd = 5.0
    budget.last_daily_reset = date.today() - timedelta(days=1)
    db.commit()

    # This should trigger a reset
    check_budget(db, api_key_id=1, estimated_cost=0.001)

    db.refresh(budget)
    assert budget.current_daily_usage_usd == 0.0
    assert budget.last_daily_reset == date.today()
