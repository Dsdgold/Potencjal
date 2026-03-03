import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(20), default="trial")  # trial/starter/growth/enterprise
    plan_status: Mapped[str] = mapped_column(String(20), default="active")  # active/past_due/canceled
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    max_users: Mapped[int] = mapped_column(Integer, default=2)
    max_regions: Mapped[int] = mapped_column(Integer, default=1)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["src.users.models.User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # type: ignore[name-defined]
    regions: Mapped[list["src.regions.models.Region"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # type: ignore[name-defined]
    leads: Mapped[list["src.leads.models.Lead"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # type: ignore[name-defined]
