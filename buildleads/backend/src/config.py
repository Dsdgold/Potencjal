"""Application configuration — all from environment variables."""

from enum import Enum

from pydantic_settings import BaseSettings


class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    MANAGER = "manager"
    SALESPERSON = "salesperson"
    VIEWER = "viewer"


class PlanType(str, Enum):
    TRIAL = "trial"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    OFFER_SENT = "offer_sent"
    WON = "won"
    LOST = "lost"
    IGNORED = "ignored"


class LeadSource(str, Enum):
    BZP = "bzp"
    TED = "ted"
    GUNB = "gunb"
    KRS = "krs"
    SCRAPING = "scraping"
    MANUAL = "manual"
    OSINT = "osint"


class MaterialCategory(str, Enum):
    CEMENT_CONCRETE = "cement_concrete"
    STEEL_METAL = "steel_metal"
    INSULATION = "insulation"
    ROOFING = "roofing"
    WINDOWS_DOORS = "windows_doors"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    FINISHING = "finishing"
    GENERAL = "general"


class LeadActionType(str, Enum):
    VIEWED = "viewed"
    CONTACTED = "contacted"
    NOTE_ADDED = "note_added"
    OFFER_SENT = "offer_sent"
    STATUS_CHANGED = "status_changed"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://buildleads:secret@localhost:5432/buildleads"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-in-production-use-long-random-string-64chars"
    jwt_algorithm: str = "HS256"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 7

    # OSINT API keys (from Potencjal)
    ceidg_api_key: str = ""
    gus_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_growth: str = ""
    stripe_price_enterprise: str = ""

    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "BuildLeads <leads@buildleads.pl>"

    # AI — Claude (primary) / Ollama (fallback)
    anthropic_api_key: str = ""
    ollama_url: str = "http://localhost:11434"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Platform admin seed
    admin_email: str = "admin@buildleads.pl"
    admin_password: str = "admin123"

    # Environment
    env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Plan configuration
PLAN_LIMITS = {
    PlanType.TRIAL: {
        "price": 0,
        "max_users": 2,
        "max_regions": 1,
        "sources": ["bzp", "gunb"],
        "email_digest": False,
        "duration_days": 14,
        "ai_queries_per_day": 5,
    },
    PlanType.STARTER: {
        "price": 49,
        "max_users": 3,
        "max_regions": 1,
        "sources": ["bzp", "gunb", "krs"],
        "email_digest": True,
        "ai_queries_per_day": 10,
    },
    PlanType.GROWTH: {
        "price": 149,
        "max_users": 10,
        "max_regions": 3,
        "sources": ["bzp", "gunb", "krs", "ted", "scraping"],
        "email_digest": True,
        "ai_queries_per_day": 50,
    },
    PlanType.ENTERPRISE: {
        "price": 399,
        "max_users": -1,  # unlimited
        "max_regions": -1,
        "sources": ["all"],
        "email_digest": True,
        "api_access": True,
        "white_label": True,
        "ai_queries_per_day": -1,  # unlimited
    },
}
