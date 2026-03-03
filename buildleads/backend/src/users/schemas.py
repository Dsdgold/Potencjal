import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str = Field(..., max_length=150)
    last_name: str = Field(..., max_length=150)
    role: str = Field("salesperson", pattern=r"^(manager|salesperson|viewer)$")
    region_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=150)
    last_name: str | None = Field(None, max_length=150)
    is_active: bool | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    region_id: uuid.UUID | None
    is_active: bool
    email_verified: bool
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
