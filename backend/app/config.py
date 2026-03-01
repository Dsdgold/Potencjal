from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://potencjal:potencjal@localhost:5432/potencjal"
    ceidg_api_key: str = ""
    gus_api_key: str = ""

    # JWT
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 7

    # First admin (created on startup if no users exist)
    admin_email: str = "admin@potencjal.pl"
    admin_password: str = "admin123"

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@potencjal.pl"
    smtp_tls: bool = True
    app_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Package limits
PACKAGE_LIMITS = {
    "starter": {"max_leads": 5, "osint": [], "bulk": False, "csv_export": False, "label": "Starter", "price": 0},
    "business": {"max_leads": 100, "osint": ["vat", "ekrs"], "bulk": False, "csv_export": True, "label": "Business", "price": 49},
    "pro": {"max_leads": 999999, "osint": ["vat", "ekrs", "ceidg", "gus"], "bulk": True, "csv_export": True, "label": "Pro", "price": 149},
    "enterprise": {"max_leads": 999999, "osint": ["vat", "ekrs", "ceidg", "gus"], "bulk": True, "csv_export": True, "label": "Enterprise", "price": 0},
}

settings = Settings()
