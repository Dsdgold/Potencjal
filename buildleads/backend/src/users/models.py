import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(150))
    last_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(20), default="salesperson")  # platform_admin/manager/salesperson/viewer
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id", ondelete="SET NULL"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["src.tenants.models.Tenant"] = relationship(back_populates="users")  # type: ignore[name-defined]
    region: Mapped["src.regions.models.Region | None"] = relationship(back_populates="users")  # type: ignore[name-defined]
