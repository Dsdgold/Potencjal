import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id", ondelete="SET NULL"), index=True)

    # Source tracking
    source: Mapped[str] = mapped_column(String(20), default="manual")  # bzp/ted/gunb/krs/scraping/manual/osint
    source_id: Mapped[str | None] = mapped_column(String(255))  # external ID from source system

    # Core fields (from Potencjal)
    nip: Mapped[str | None] = mapped_column(String(10), index=True)
    name: Mapped[str] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    voivodeship: Mapped[str | None] = mapped_column(String(50))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Address
    street: Mapped[str | None] = mapped_column(String(200))
    postal_code: Mapped[str | None] = mapped_column(String(10))

    # Registry identifiers
    regon: Mapped[str | None] = mapped_column(String(14))
    krs: Mapped[str | None] = mapped_column(String(10))
    legal_form: Mapped[str | None] = mapped_column(String(200))

    # Company data
    employees: Mapped[int | None] = mapped_column(Integer)
    revenue_pln: Mapped[float | None] = mapped_column(Float)
    revenue_band: Mapped[str | None] = mapped_column(String(20))
    pkd: Mapped[str | None] = mapped_column(String(10))
    pkd_desc: Mapped[str | None] = mapped_column(String(300))
    years_active: Mapped[float | None] = mapped_column(Float)
    vat_status: Mapped[str | None] = mapped_column(String(30))
    website: Mapped[str | None] = mapped_column(String(300))

    # People & social
    board_members: Mapped[list | None] = mapped_column(JSONB, default=list)
    social_media: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # New BuildLeads fields
    title: Mapped[str | None] = mapped_column(String(500))  # tender title
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))  # MaterialCategory
    subcategory: Mapped[str | None] = mapped_column(String(100))
    estimated_value: Mapped[float | None] = mapped_column(Float)
    cpv_codes: Mapped[list | None] = mapped_column(JSONB, default=list)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Contact
    contact_company: Mapped[str | None] = mapped_column(String(300))
    contact_person: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    contact_email: Mapped[str | None] = mapped_column(String(255))

    # Scoring (from Potencjal scoring engine)
    basket_pln: Mapped[float | None] = mapped_column(Float, default=0)
    score: Mapped[int | None] = mapped_column(Integer)  # 0-100 (Potencjal) or 1-10 (AI)
    tier: Mapped[str | None] = mapped_column(String(1))  # S/A/B/C
    annual_potential: Mapped[int | None] = mapped_column(Integer)
    ai_summary: Mapped[str | None] = mapped_column(Text)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="new")  # LeadStatus enum
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # OSINT data (from Potencjal)
    osint_raw: Mapped[dict | None] = mapped_column(JSONB)
    sources: Mapped[list | None] = mapped_column(JSONB, default=list)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)  # raw data from collector

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant: Mapped["src.tenants.models.Tenant"] = relationship(back_populates="leads")  # type: ignore[name-defined]
    region: Mapped["src.regions.models.Region | None"] = relationship(back_populates="leads")  # type: ignore[name-defined]
    actions: Mapped[list["LeadAction"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    scoring_history: Mapped[list["ScoringHistory"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


class LeadAction(Base):
    __tablename__ = "lead_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(30))  # LeadActionType
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="actions")


class ScoringHistory(Base):
    """Ported from Potencjal — tracks every scoring event per lead."""
    __tablename__ = "scoring_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(1))
    annual_potential: Mapped[int] = mapped_column(Integer)
    weights_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="scoring_history")
