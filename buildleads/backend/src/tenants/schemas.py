import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    plan_status: str
    max_users: int
    max_regions: int
    trial_ends_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = Field(None, max_length=300)
    plan: str | None = None
    is_active: bool | None = None
