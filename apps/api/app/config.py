from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str = "postgresql+asyncpg://potencjal:potencjal@localhost:5432/potencjal"
    DATABASE_URL_SYNC: str = "postgresql://potencjal:potencjal@localhost:5432/potencjal"
    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
    SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Providers
    VAT_API_BASE_URL: str = "https://wl-api.mf.gov.pl"
    GUS_API_KEY: str = ""
    GUS_API_URL: str = "https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewnworki.svc"
    KRS_API_BASE_URL: str = "https://api-krs.ms.gov.pl/api/krs"
    CEIDG_API_KEY: str = ""
    CEIDG_API_URL: str = "https://dane.biznes.gov.pl/api/ceidg/v2"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PRO_MONTHLY: str = ""
    STRIPE_PRICE_ENTERPRISE_MONTHLY: str = ""

    # Embedding
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    OPENAI_API_KEY: str = ""

    # Encryption
    CREDENTIALS_ENCRYPTION_KEY: str = ""

    # Cache
    SNAPSHOT_TTL_SECONDS: int = 86400

    # Sentry
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
