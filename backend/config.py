"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings for the sandbox-only Pactra application."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: str = "development-only-change-me-32-bytes"

    database_url: str = "sqlite:///./pactra.db"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    ai_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    max_chat_history: int = 20

    paypal_payouts_enabled: bool = False
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_test_recipient_email: str = ""
    paypal_request_timeout_seconds: float = 15.0
    # Retained only for local compatibility while the provider adapter is
    # migrated. Production readiness never treats mock IDs as PayPal results.
    paypal_mock_mode: bool = True

    session_cookie_secure: bool = False
    session_ttl_hours: int = 168
    session_idle_hours: int = 24
    policy_config_path: str = "./backend/policy.json"
    seed_demo_account: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """Accept either a comma-separated env value or a JSON-style list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def normalise_database_url(cls, value: str) -> str:
        """Normalise host-provided PostgreSQL URLs for SQLAlchemy/psycopg."""
        value = value.strip()
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://") and "+psycopg" not in value:
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @model_validator(mode="after")
    def enforce_sandbox_provider_configuration(self) -> "Settings":
        """Reject unsafe production PayPal configuration at startup."""
        sandbox_url = "https://api-m.sandbox.paypal.com"
        if self.app_env == "production":
            if self.is_sqlite:
                raise ValueError("Production must use PostgreSQL, not SQLite")
            if self.paypal_base_url.rstrip("/") != sandbox_url:
                raise ValueError("Production must use the PayPal Sandbox API host")
            if self.paypal_mock_mode:
                raise ValueError("PAYPAL_MOCK_MODE cannot be enabled in production")
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 characters")
        if self.paypal_payouts_enabled:
            if self.paypal_mock_mode:
                raise ValueError(
                    "PAYPAL_MOCK_MODE must be false when PayPal Payouts is enabled"
                )
            if not self.paypal_client_id or not self.paypal_client_secret:
                raise ValueError(
                    "PayPal sandbox client credentials are required when payouts are enabled"
                )
            if not self.paypal_test_recipient_email:
                raise ValueError(
                    "PAYPAL_TEST_RECIPIENT_EMAIL is required when payouts are enabled"
                )
        if self.ai_enabled and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_ENABLED is true")
        if self.ai_enabled and self.gemini_model != "gemini-3.8-flash":
            raise ValueError("AI_ENABLED requires the configured gemini-3.8-flash model")
        return self

    @property
    def resolved_policy_path(self) -> Path:
        path = Path(self.policy_config_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
