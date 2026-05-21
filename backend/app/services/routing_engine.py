from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.model import Model
from app.models.routing_rule import RoutingRule
from app.services.circuit_breaker import circuit_breaker


@dataclass
class RoutingDecision:
    model_id: int
    model_name: str
    provider_id: int
    fallback_chain: list[int]
    strategy_used: str
    was_fallback: bool = False


def route_request(
    db: Session,
    strategy: str = "balanced",
    industry: str = "",
    task_type: str = "",
    model_override: str = "",
) -> RoutingDecision:
    # Direct model override
    if model_override:
        model = db.query(Model).filter(Model.name == model_override).first()
        if model:
            return RoutingDecision(
                model_id=model.id,
                model_name=model.name,
                provider_id=model.provider_id,
                fallback_chain=[],
                strategy_used="override",
            )

    # Try industry x task_type routing rule
    if industry and task_type:
        rule = (
            db.query(RoutingRule)
            .filter(RoutingRule.industry == industry, RoutingRule.task_type == task_type)
            .first()
        )
        if rule:
            primary = db.query(Model).filter(Model.id == rule.primary_model_id).first()
            if primary and circuit_breaker.is_available(primary.provider_id):
                return RoutingDecision(
                    model_id=primary.id,
                    model_name=primary.name,
                    provider_id=primary.provider_id,
                    fallback_chain=[rule.fallback_model_id, rule.specialist_model_id],
                    strategy_used=f"rule:{industry}/{task_type}",
                )
            # Primary unavailable, try fallback
            fallback = db.query(Model).filter(Model.id == rule.fallback_model_id).first()
            if fallback and circuit_breaker.is_available(fallback.provider_id):
                return RoutingDecision(
                    model_id=fallback.id,
                    model_name=fallback.name,
                    provider_id=fallback.provider_id,
                    fallback_chain=[rule.specialist_model_id],
                    strategy_used=f"rule:{industry}/{task_type}",
                    was_fallback=True,
                )
            # Use specialist
            specialist = db.query(Model).filter(Model.id == rule.specialist_model_id).first()
            if specialist:
                return RoutingDecision(
                    model_id=specialist.id,
                    model_name=specialist.name,
                    provider_id=specialist.provider_id,
                    fallback_chain=[],
                    strategy_used=f"rule:{industry}/{task_type}",
                    was_fallback=True,
                )

    # Strategy-based routing
    models = db.query(Model).all()
    available_models = [m for m in models if circuit_breaker.is_available(m.provider_id)]
    if not available_models:
        available_models = models  # fallback to all if none available

    if not available_models:
        raise ValueError("No models available")

    if strategy == "cost_optimized":
        selected = sorted(available_models, key=lambda m: m.cost_per_1k_input)[0]
    elif strategy == "quality_optimized":
        selected = sorted(available_models, key=lambda m: m.quality_score, reverse=True)[0]
    elif strategy == "latency_optimized":
        selected = sorted(available_models, key=lambda m: m.avg_latency_ms)[0]
    else:  # balanced
        def balanced_score(m: Model) -> float:
            max_cost = max(x.cost_per_1k_input for x in available_models) or 1
            normalized_cost = m.cost_per_1k_input / max_cost if max_cost > 0 else 0
            return 0.4 * m.quality_score + 0.3 * (1 - normalized_cost) + 0.3 * m.speed_score

        selected = sorted(available_models, key=balanced_score, reverse=True)[0]

    # Build fallback chain from remaining models
    fallback_ids = [m.id for m in available_models if m.id != selected.id][:2]

    return RoutingDecision(
        model_id=selected.id,
        model_name=selected.name,
        provider_id=selected.provider_id,
        fallback_chain=fallback_ids,
        strategy_used=strategy,
    )


def try_fallback(db: Session, fallback_chain: list[int]) -> Optional[RoutingDecision]:
    for model_id in fallback_chain:
        model = db.query(Model).filter(Model.id == model_id).first()
        if model and circuit_breaker.is_available(model.provider_id):
            remaining = [mid for mid in fallback_chain if mid != model_id]
            return RoutingDecision(
                model_id=model.id,
                model_name=model.name,
                provider_id=model.provider_id,
                fallback_chain=remaining,
                strategy_used="fallback",
                was_fallback=True,
            )
    return None
