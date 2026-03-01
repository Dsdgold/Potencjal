import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nip: Mapped[str | None] = mapped_column(String(10), index=True)
    name: Mapped[str] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    employees: Mapped[int | None] = mapped_column(Integer)
    revenue_pln: Mapped[float | None] = mapped_column(Float)
    revenue_band: Mapped[str | None] = mapped_column(String(20))
    pkd: Mapped[str | None] = mapped_column(String(10))
    pkd_desc: Mapped[str | None] = mapped_column(String(300))
    years_active: Mapped[float | None] = mapped_column(Float)
    vat_status: Mapped[str | None] = mapped_column(String(30))
    website: Mapped[str | None] = mapped_column(String(300))
    basket_pln: Mapped[float | None] = mapped_column(Float, default=0)
    score: Mapped[int | None] = mapped_column(Integer)
    tier: Mapped[str | None] = mapped_column(String(1))
    annual_potential: Mapped[int | None] = mapped_column(Integer)
    osint_raw: Mapped[dict | None] = mapped_column(JSONB)
    sources: Mapped[list | None] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    scoring_history: Mapped[list["ScoringHistory"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


class ScoringHistory(Base):
    __tablename__ = "scoring_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(1))
    annual_potential: Mapped[int] = mapped_column(Integer)
    weights_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="scoring_history")
