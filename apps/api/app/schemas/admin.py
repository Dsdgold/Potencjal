from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class PlanResponse(BaseModel):
    id: UUID
    code: str
    name: str
    limits_json: dict
    features_json: dict
    price_monthly: int
    is_public: bool

    class Config:
        from_attributes = True


class OrgResponse(BaseModel):
    id: UUID
    name: str
    plan_id: UUID | None
    plan_name: str | None = None
    status: str
    user_count: int = 0
    lookup_count_this_month: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class OrgUpdate(BaseModel):
    name: str | None = None
    plan_id: UUID | None = None
    status: str | None = None


class UserAdminResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    org_id: UUID | None
    org_name: str | None = None
    last_login: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class UserAdminUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    org_id: UUID | None = None


class OverrideCreate(BaseModel):
    field_path: str = Field(min_length=1)
    value_json: dict
    reason: str = Field(min_length=1)


class OverrideResponse(BaseModel):
    id: UUID
    company_id: UUID
    field_path: str
    value_json: dict
    reason: str
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: str
    diff_json: dict | None
    ip_address: str | None
    purpose: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ScoringConfigUpdate(BaseModel):
    weights: dict[str, float]
    thresholds: dict[str, float] | None = None


class SystemHealthResponse(BaseModel):
    db_status: str
    redis_status: str
    qdrant_status: str
    queue_depth: int
    provider_errors_24h: int
    active_orgs: int
    lookups_today: int
