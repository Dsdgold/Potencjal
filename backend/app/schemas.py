import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Lead ──────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    nip: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")
    name: str = Field(..., max_length=300)
    city: str | None = Field(None, max_length=100)
    employees: int | None = Field(None, ge=0)
    revenue_pln: float | None = Field(None, ge=0)
    revenue_band: str | None = None
    pkd: str | None = Field(None, max_length=10)
    pkd_desc: str | None = None
    years_active: float | None = Field(None, ge=0)
    vat_status: str | None = None
    website: str | None = None
    basket_pln: float | None = Field(0, ge=0)
    notes: str | None = None


class LeadUpdate(BaseModel):
    nip: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")
    name: str | None = Field(None, max_length=300)
    city: str | None = None
    employees: int | None = Field(None, ge=0)
    revenue_pln: float | None = Field(None, ge=0)
    revenue_band: str | None = None
    pkd: str | None = None
    pkd_desc: str | None = None
    years_active: float | None = Field(None, ge=0)
    vat_status: str | None = None
    website: str | None = None
    basket_pln: float | None = Field(None, ge=0)
    notes: str | None = None


class LeadOut(BaseModel):
    id: uuid.UUID
    nip: str | None
    name: str
    city: str | None
    employees: int | None
    revenue_pln: float | None
    revenue_band: str | None
    pkd: str | None
    pkd_desc: str | None
    years_active: float | None
    vat_status: str | None
    website: str | None
    basket_pln: float | None
    score: int | None
    tier: str | None
    annual_potential: int | None
    sources: list[str] | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadList(BaseModel):
    items: list[LeadOut]
    total: int


# ── Scoring ───────────────────────────────────────────────────────────

class ScoringRequest(BaseModel):
    employees: int = Field(0, ge=0)
    revenue_pln: float = Field(0, ge=0)
    years_active: float = Field(0, ge=0)
    vat_status: str = "Niepewny"
    pkd: str = ""
    basket_pln: float = Field(0, ge=0)
    locality_hit: bool = False


class ScoringResult(BaseModel):
    score: int
    tier: str
    annual_potential: int
    revenue_band: str
    categories: list[str]
    recommended_actions: list[str]


class ScoringHistoryOut(BaseModel):
    id: uuid.UUID
    score: int
    tier: str
    annual_potential: int
    weights_snapshot: dict | None
    scored_at: datetime

    model_config = {"from_attributes": True}


# ── OSINT ─────────────────────────────────────────────────────────────

class OsintResult(BaseModel):
    source: str
    nip: str | None = None
    name: str | None = None
    city: str | None = None
    employees: int | None = None
    revenue_pln: float | None = None
    pkd: str | None = None
    pkd_desc: str | None = None
    years_active: float | None = None
    vat_status: str | None = None
    website: str | None = None
    regon: str | None = None
    krs: str | None = None
    raw: dict | None = None


class EnrichResponse(BaseModel):
    results: list[OsintResult]
    merged: LeadUpdate
