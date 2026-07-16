"""
api/config.py — Centralized Pydantic Settings Configuration for ABSs v2.0.

Single authoritative source of settings reading from environment variables
and `.env` files. Validates configuration at startup and fails fast on invalid
or missing parameters.
"""

import os
from typing import Any, List, Optional, Union
from urllib.parse import quote_plus
from pydantic import Field, field_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_JWT_SECRETS = {
    "super-secret-key-replace-in-production-1234567890",
    "secret",
    "password",
    "changeme",
    "abs_secret_change_me",
    "abs_secret",
    "1234567890",
    "test-secret",
    "dev-secret",
    "default-secret-key"
}


class Settings(BaseSettings):
    """
    Centralized application configuration settings.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment & Application Info
    ENV: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
        description="Environment mode (development, staging, production)"
    )
    DEBUG: bool = Field(default=False, description="Debug mode flag")

    # Database Configuration
    DATABASE_URL: Optional[str] = Field(default=None, description="Explicit database URL override")
    USE_SQLITE: bool = Field(
        default_factory=lambda: os.getenv("USE_SQLITE", "false").lower() == "true" or (os.name == "nt" and not os.getenv("DATABASE_URL")),
        description="Whether to fall back to local SQLite"
    )
    POSTGRES_USER: str = Field(default="abs_user", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="abs_secret_change_me", description="PostgreSQL password")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL hostname")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port number")
    POSTGRES_DB: str = Field(default="abs_db", description="PostgreSQL database name")

    DB_ECHO: bool = Field(default=False, description="Whether to echo SQL queries")
    DB_POOL_SIZE: int = Field(default=10, description="PostgreSQL connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="PostgreSQL connection pool max overflow")

    # Redis & Celery Workers
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Redis broker URL for Celery")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1", description="Redis backend URL for Celery")

    # CORS (Task 1.6)
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"],
        description="Allowed CORS origins"
    )

    # Security & Authentication (Legacy & Phase 2 preparation)
    VIRUSTOTAL_API_KEY: str = Field(default="", description="VirusTotal API Key")
    JWT_SECRET_KEY: str = Field(
        default="super-secret-key-replace-in-production-1234567890",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
        description="Secret key for JWT tokens"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token TTL in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token TTL in days")

    # Phase 3 Rate Limiting Configuration (Tasks 3.1 - 3.5 & Section 8)
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable API rate limiting")
    REDIS_POOL_SIZE: int = Field(default=20, description="Max Redis async connection pool size (Task 3.5)")
    LOGIN_RATE_LIMIT: int = Field(default=10, description="Max login/auth requests per window (Task 3.2)")
    LOGIN_RATE_WINDOW: int = Field(default=60, description="Login/auth rate window in seconds")
    WORKER_LIMIT: int = Field(default=5, description="Max session/worker creations per window (Task 3.2)")
    WORKER_RATE_WINDOW: int = Field(default=60, description="Worker rate window in seconds")
    WORKER_MAX_CONCURRENT_TASKS_PER_TENANT: int = Field(default=5, description="Max concurrent tasks allowed per tenant")
    TENANT_CREATE_LIMIT: int = Field(default=2, description="Max tenant creations per window (Task 3.2)")
    TENANT_CREATE_WINDOW: int = Field(default=3600, description="Tenant creation window in seconds")
    TENANT_REQUEST_LIMIT: int = Field(default=200, description="Default tenant quota per minute")
    TENANT_REQUEST_WINDOW: int = Field(default=60, description="Default tenant quota window in seconds")
    API_KEY_LIMIT: int = Field(default=300, description="Max requests per API key per window")
    API_KEY_WINDOW: int = Field(default=60, description="API key rate window in seconds")
    DEFAULT_RATE_LIMIT: int = Field(default=200, description="Default max requests per window (Task 3.2)")
    DEFAULT_RATE_WINDOW: int = Field(default=60, description="Default rate window in seconds")
    BURST_LIMIT: int = Field(default=50, description="Burst traffic limit max requests")
    BURST_WINDOW: int = Field(default=10, description="Burst traffic window in seconds")
    SUSTAINED_LIMIT: int = Field(default=500, description="Sustained traffic limit max requests")
    SUSTAINED_WINDOW: int = Field(default=300, description="Sustained traffic window in seconds")

    # Agent / LLM Configuration
    AGENT_LLM_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Model name for browser automation agent")
    AGENT_MAX_STEPS: int = Field(default=25, description="Maximum browser steps allowed per session")
    LLM_PROVIDER: str = Field(default="groq", description="Default LLM provider")
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    GEMINI_API_KEY: str = Field(default="", description="Gemini API Key")
    XAI_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Model name for XAI explanation generator")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def get_database_url(self) -> str:
        """
        Constructs the authoritative async database URL based on configuration settings.
        """
        if self.DATABASE_URL and not self.USE_SQLITE:
            return self.DATABASE_URL

        if not self.USE_SQLITE:
            if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB and self.POSTGRES_HOST != "localhost":
                return (
                    f"postgresql+asyncpg://{quote_plus(self.POSTGRES_USER)}:{quote_plus(self.POSTGRES_PASSWORD)}"
                    f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
                )
            # If explicit POSTGRES_HOST is provided or USE_SQLITE is explicitly false and not windows default
            if not (os.name == "nt" and self.POSTGRES_HOST == "localhost" and not self.DATABASE_URL):
                return (
                    f"postgresql+asyncpg://{quote_plus(self.POSTGRES_USER)}:{quote_plus(self.POSTGRES_PASSWORD)}"
                    f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
                )

        # Default fallback: aiosqlite for local development and test execution
        return "sqlite+aiosqlite:///./abs_security.db"

    def validate_production_secrets(self) -> None:
        """
        Validate high-severity security configuration upon startup.
        If running in production mode (ENV == "production"), abort startup immediately
        if insecure, missing, or short JWT secrets are detected.
        """
        env_mode = self.ENV.lower().strip()
        if env_mode == "production":
            if not self.JWT_SECRET_KEY or not self.JWT_SECRET_KEY.strip():
                raise RuntimeError(
                    f"FATAL SECURITY MISCONFIGURATION: JWT_SECRET_KEY is missing or empty in '{self.ENV}' environment. "
                    f"Application startup aborted."
                )
            if self.JWT_SECRET_KEY.strip() in INSECURE_DEFAULT_JWT_SECRETS:
                raise RuntimeError(
                    f"FATAL SECURITY MISCONFIGURATION: JWT_SECRET_KEY cannot use development fallback or default values in '{self.ENV}' environment. "
                    f"Please provide a secure, cryptographically random secret of at least 32 characters."
                )
            if len(self.JWT_SECRET_KEY.strip()) < 32:
                raise RuntimeError(
                    f"FATAL SECURITY MISCONFIGURATION: JWT_SECRET_KEY must be at least 32 characters long in '{self.ENV}' environment (current length: {len(self.JWT_SECRET_KEY.strip())}). "
                    f"Application startup aborted."
                )

    def validate_production_environment(self) -> None:
        """
        Validate complete production environment configuration and deployment readiness (Phase 7 Task 10).
        Fails fast if critical secrets, database credentials, or CORS policies are misconfigured in production.
        """
        self.validate_production_secrets()
        env_mode = self.ENV.lower().strip()
        if env_mode == "production":
            # Validate database credentials if connecting to an external production database
            if self.POSTGRES_HOST != "localhost" and self.POSTGRES_PASSWORD in ["abs_secret_change_me", "postgres", "password", "123456", ""]:
                raise RuntimeError(
                    f"FATAL SECURITY MISCONFIGURATION: POSTGRES_PASSWORD cannot use default or weak password in '{self.ENV}' environment."
                )
            if "*" in self.CORS_ORIGINS:
                raise RuntimeError(
                    f"FATAL SECURITY MISCONFIGURATION: CORS_ORIGINS cannot allow wildcard '*' in '{self.ENV}' environment."
                )

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        self.validate_production_secrets()


# Global singleton settings instance
settings = Settings()
