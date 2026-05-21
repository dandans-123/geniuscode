from __future__ import annotations

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.5)
    speed_score: Mapped[float] = mapped_column(Float, default=0.5)
    cost_per_1k_input: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_1k_output: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=1000)
    tokens_per_second: Mapped[int] = mapped_column(Integer, default=50)
    max_context_length: Mapped[int] = mapped_column(Integer, default=4096)
    capabilities: Mapped[str] = mapped_column(Text, default="[]")  # JSON text
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)

    provider = relationship("Provider", back_populates="models")
