from __future__ import annotations

from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoutingRule(Base):
    __tablename__ = "routing_rules"
    __table_args__ = (UniqueConstraint("industry", "task_type", name="uq_industry_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    industry: Mapped[str] = mapped_column(String(50), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    primary_model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), nullable=False)
    fallback_model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), nullable=False)
    specialist_model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    speed_score: Mapped[float] = mapped_column(Float, default=0.0)
    cost_score: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    estimated_cost: Mapped[str] = mapped_column(String(50), default="")

    primary_model = relationship("Model", foreign_keys=[primary_model_id])
    fallback_model = relationship("Model", foreign_keys=[fallback_model_id])
    specialist_model = relationship("Model", foreign_keys=[specialist_model_id])
