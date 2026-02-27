from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class NIPLookupRequest(BaseModel):
    nip: str = Field(pattern=r"^\d{10}$", description="10-digit Polish NIP")
    purpose: str = Field(default="credit_assessment", description="GDPR purpose of lookup")


class CompanyOverview(BaseModel):
    id: UUID
    nip: str
    name: str | None
    regon: str | None
    krs: str | None
    country: str
    legal_form: str | None
    pkd_main: str | None
    pkd_codes: list[str] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SnapshotData(BaseModel):
    """Normalized company data from all sources."""
    # Basic identity
    name: str | None = None
    nip: str | None = None
    regon: str | None = None
    krs: str | None = None
    legal_form: str | None = None
    legal_form_code: str | None = None

    # VAT
    vat_status: str | None = None
    vat_status_date: str | None = None

    # Addresses
    registered_address: str | None = None
    business_address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    voivodeship: str | None = None

    # Dates
    registration_date: str | None = None
    start_date: str | None = None
    krs_registration_date: str | None = None

    # Financial indicators
    share_capital: float | None = None
    share_capital_currency: str | None = None
    annual_revenue_estimate: float | None = None
    employee_count_range: str | None = None

    # PKD / industry
    pkd_main_code: str | None = None
    pkd_main_name: str | None = None
    pkd_codes: list[dict] | None = None

    # Management
    representatives: list[dict] | None = None
    partners: list[dict] | None = None
    beneficial_owners: list[str] | None = None

    # Banking
    bank_accounts: list[str] | None = None
    bank_account_count: int | None = None

    # Contact (only if from official sources)
    email: str | None = None
    phone: str | None = None
    website: str | None = None

    # Tenders (from public procurement)
    recent_tenders: list[dict] | None = None

    # Status flags
    is_active: bool | None = None
    has_vat_registration: bool | None = None
    is_in_krs: bool | None = None
    is_in_ceidg: bool | None = None


class SourceInfo(BaseModel):
    provider: str
    fetched_at: str
    status: str
    fields_count: int


class QualityInfo(BaseModel):
    completeness_pct: float
    sources_count: int
    freshness_hours: float
    confidence: str


class CompanyProfileResponse(BaseModel):
    company: CompanyOverview
    snapshot: SnapshotData
    sources: list[SourceInfo]
    quality: QualityInfo
    score: "ScoreResponse | None" = None
    materials: "MaterialResponse | None" = None


class ScoreComponent(BaseModel):
    name: str
    label_pl: str
    points: float
    max_points: float
    explanation: str


class ScoreResponse(BaseModel):
    score_0_100: int
    risk_band: str
    risk_band_label: str
    credit_limit_suggested: int
    credit_limit_min: int
    credit_limit_max: int
    payment_terms_days: int
    discount_pct: float
    components: list[ScoreComponent]
    red_flags: list[str]
    green_flags: list[str]
    explanation_summary: str


class MaterialCategory(BaseModel):
    code: str
    name_pl: str
    confidence: float
    reason: str


class MaterialResponse(BaseModel):
    categories: list[MaterialCategory]
    explanation: str


class NoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    tags: list[str] | None = None


class NoteResponse(BaseModel):
    id: UUID
    company_id: UUID
    user_id: UUID
    text: str
    tags_json: list[str] | None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    assigned_user_id: UUID | None = None
    due_at: datetime | None = None


class TaskResponse(BaseModel):
    id: UUID
    company_id: UUID
    title: str
    description: str | None
    assigned_user_id: UUID | None
    due_at: datetime | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str | None = None
    company_nip: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# Forward references
CompanyProfileResponse.model_rebuild()
