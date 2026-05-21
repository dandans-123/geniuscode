from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.auth_service import verify_admin_key
from app.models.routing_rule import RoutingRule
from app.schemas.routing_rule import RoutingRuleCreate, RoutingRuleUpdate, RoutingRuleResponse

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get("/routing-rules", response_model=list[RoutingRuleResponse])
def list_routing_rules(
    industry: str = Query(default=None),
    task_type: str = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(RoutingRule)
    if industry:
        query = query.filter(RoutingRule.industry == industry)
    if task_type:
        query = query.filter(RoutingRule.task_type == task_type)
    return query.all()


@router.get("/routing-rules/{rule_id}", response_model=RoutingRuleResponse)
def get_routing_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return rule


@router.post("/routing-rules", response_model=RoutingRuleResponse)
def create_routing_rule(data: RoutingRuleCreate, db: Session = Depends(get_db)):
    rule = RoutingRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/routing-rules/{rule_id}", response_model=RoutingRuleResponse)
def update_routing_rule(rule_id: int, data: RoutingRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/routing-rules/{rule_id}")
def delete_routing_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    db.delete(rule)
    db.commit()
    return {"detail": "deleted"}
