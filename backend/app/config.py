from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Investment & Wealth Intelligence Platform"
    VERSION: str = "1.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "super_secret_jwt_key_change_in_production_min_32_chars_long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for personal dev
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALLOW_PUBLIC_REGISTRATION: bool = True
    DOCS_ENABLED: bool = True
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20
    AI_RATE_LIMIT_PER_MINUTE: int = 30

    def validate_production_security(self) -> None:
        """Fail fast on insecure defaults when running in production."""
        if self.ENVIRONMENT.lower() == "production":
            if (
                not self.SECRET_KEY
                or len(self.SECRET_KEY) < 32
                or self.SECRET_KEY.startswith("super_secret_jwt_key")
            ):
                raise RuntimeError(
                    "Production startup blocked: SECRET_KEY must be set to a strong, unique >=32-char value."
                )
            if self.POSTGRES_PASSWORD == "postgres_secret_change_me":
                raise RuntimeError(
                    "Production startup blocked: POSTGRES_PASSWORD must not use the default development secret."
                )

    # Default Reporting Currency
    DEFAULT_REPORTING_CURRENCY: str = "GHS"

    # PostgreSQL Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secret_change_me"
    POSTGRES_DB: str = "finance_tracker"
    DATABASE_URL: Union[str, None] = None

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            return self.DATABASE_URL
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # AI & External Data Providers (Optional: Graceful fallback when unset)
    AI_PROVIDER: str = "openai"  # openai, gemini, local_fallback
    AI_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: Union[str, None] = None
    GEMINI_API_KEY: Union[str, None] = None
    FRED_API_KEY: Union[str, None] = None

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
