import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    voivodeships: Mapped[list | None] = mapped_column(JSONB, default=list)  # e.g. ["mazowieckie", "lubelskie"]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["src.tenants.models.Tenant"] = relationship(back_populates="regions")  # type: ignore[name-defined]
    users: Mapped[list["src.users.models.User"]] = relationship(back_populates="region")  # type: ignore[name-defined]
    leads: Mapped[list["src.leads.models.Lead"]] = relationship(back_populates="region")  # type: ignore[name-defined]
