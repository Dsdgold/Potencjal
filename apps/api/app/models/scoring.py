import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ScoreResult(Base):
    __tablename__ = "score_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_snapshots.id"), nullable=False)
    score_version: Mapped[str] = mapped_column(String(20), default="v1")
    score_0_100: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_band: Mapped[str] = mapped_column(String(5), nullable=False)
    credit_limit_suggested: Mapped[int] = mapped_column(Integer, default=0)
    credit_limit_min: Mapped[int] = mapped_column(Integer, default=0)
    credit_limit_max: Mapped[int] = mapped_column(Integer, default=0)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=0)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    components_json: Mapped[dict] = mapped_column(JSON, default=dict)
    red_flags: Mapped[list] = mapped_column(JSON, default=list)
    green_flags: Mapped[list] = mapped_column(JSON, default=list)
    explanation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MaterialRecommendation(Base):
    __tablename__ = "material_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_snapshots.id"), nullable=False)
    categories_json: Mapped[list] = mapped_column(JSON, default=list)
    explanation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
