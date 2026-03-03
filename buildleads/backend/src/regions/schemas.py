import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RegionCreate(BaseModel):
    name: str = Field(..., max_length=200)
    voivodeships: list[str] = Field(default_factory=list)


class RegionUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    voivodeships: list[str] | None = None


class RegionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    voivodeships: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}
