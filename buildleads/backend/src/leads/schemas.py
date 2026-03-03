import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    # Source
    source: str = "manual"
    source_id: str | None = None

    # Company (from Potencjal)
    nip: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")
    name: str = Field(..., max_length=300)
    city: str | None = Field(None, max_length=100)
    voivodeship: str | None = None
    employees: int | None = Field(None, ge=0)
    revenue_pln: float | None = Field(None, ge=0)
    revenue_band: str | None = None
    pkd: str | None = Field(None, max_length=10)
    pkd_desc: str | None = None
    years_active: float | None = Field(None, ge=0)
    vat_status: str | None = None
    website: str | None = None
    basket_pln: float | None = Field(0, ge=0)

    # New BuildLeads fields
    title: str | None = None
    description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    estimated_value: float | None = None
    cpv_codes: list[str] | None = None
    deadline: datetime | None = None

    # Contact
    contact_company: str | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None

    region_id: uuid.UUID | None = None
    notes: str | None = None


class LeadUpdate(BaseModel):
    name: str | None = Field(None, max_length=300)
    city: str | None = None
    voivodeship: str | None = None
    employees: int | None = Field(None, ge=0)
    revenue_pln: float | None = Field(None, ge=0)
    pkd: str | None = None
    pkd_desc: str | None = None
    years_active: float | None = None
    vat_status: str | None = None
    website: str | None = None
    basket_pln: float | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    estimated_value: float | None = None
    contact_person: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    nip: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")


class LeadOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    region_id: uuid.UUID | None
    source: str
    nip: str | None
    name: str
    city: str | None
    voivodeship: str | None
    employees: int | None
    revenue_pln: float | None
    revenue_band: str | None
    pkd: str | None
    pkd_desc: str | None
    years_active: float | None
    vat_status: str | None
    website: str | None
    basket_pln: float | None
    title: str | None
    description: str | None
    category: str | None
    estimated_value: float | None
    deadline: datetime | None
    contact_company: str | None
    contact_person: str | None
    contact_phone: str | None
    contact_email: str | None
    score: int | None
    tier: str | None
    annual_potential: int | None
    status: str
    ai_summary: str | None
    sources: list[str] | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadList(BaseModel):
    items: list[LeadOut]
    total: int


class LeadActionCreate(BaseModel):
    action: str
    note: str | None = None


class LeadActionOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoringHistoryOut(BaseModel):
    id: uuid.UUID
    score: int
    tier: str
    annual_potential: int
    weights_snapshot: dict | None
    scored_at: datetime

    model_config = {"from_attributes": True}
