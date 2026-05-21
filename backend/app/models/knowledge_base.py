from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_keys.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    industry: Mapped[str] = mapped_column(String(40), default="general", index=True)
    skills: Mapped[str] = mapped_column(Text, default="[]")
    embed: Mapped[str] = mapped_column(String(50), default="bge-m3")
    visibility: Mapped[str] = mapped_column(String(20), default="private", index=True)
    attached: Mapped[bool] = mapped_column(Boolean, default=False)
    publish_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_price_mode: Mapped[str] = mapped_column(String(20), default="free")
    publish_price: Mapped[int] = mapped_column(Integer, default=0)
    author: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribers_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[int] = mapped_column(Integer, default=0)  # *10 for one decimal
    cover_idx: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="kb", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    kb_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(10), default="txt")
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    kb: Mapped[KnowledgeBase] = relationship("KnowledgeBase", back_populates="documents")


class KBSubscription(Base):
    __tablename__ = "kb_subscriptions"
    __table_args__ = (UniqueConstraint("api_key_id", "kb_id", name="uq_subscriber_kb"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), index=True, nullable=False)
    kb_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
