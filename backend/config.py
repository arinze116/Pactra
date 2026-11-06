"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from stat import S_IMODE
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SECRET_KEY = "development-only-change-me-32-bytes"


class Settings(BaseSettings):
    """Runtime settings for the sandbox-only Pactra application."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: str = DEFAULT_SECRET_KEY
    secret_key_file: str = ""

    database_url: str = "sqlite:///./pactra.db"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    ai_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_request_timeout_seconds: float = Field(default=12.0, gt=0, le=60)
    max_chat_history: int = Field(default=20, ge=1, le=100)

    paypal_payouts_enabled: bool = False
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    paypal_test_recipient_email: str = ""
    paypal_request_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    # Retained only for local compatibility while the provider adapter is
    # migrated. Production readiness never treats mock IDs as PayPal results.
    paypal_mock_mode: bool = True

    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_ttl_hours: int = Field(default=168, gt=0, le=720)
    session_idle_hours: int = Field(default=24, gt=0, le=168)
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

    @field_validator("frontend_url", "backend_url")
    @classmethod
    def normalise_origin(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @model_validator(mode="after")
    def enforce_sandbox_provider_configuration(self) -> "Settings":
        """Reject unsafe production PayPal configuration at startup."""
        if self.secret_key_file:
            secret_path = Path(self.secret_key_file)
            if not secret_path.is_absolute():
                raise ValueError("SECRET_KEY_FILE must be an absolute path")
            try:
                insecure_mode = S_IMODE(secret_path.stat().st_mode) & 0o077
                if self.app_env == "production" and insecure_mode:
                    raise ValueError(
                        "SECRET_KEY_FILE must not be readable by group or other users"
                    )
                self.secret_key = secret_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ValueError("SECRET_KEY_FILE could not be read") from exc
        sandbox_url = "https://api-m.sandbox.paypal.com"
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError(
                "SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true"
            )
        if self.session_idle_hours > self.session_ttl_hours:
            raise ValueError("SESSION_IDLE_HOURS cannot exceed SESSION_TTL_HOURS")
        if self.app_env == "production":
            if self.is_sqlite:
                raise ValueError("Production must use PostgreSQL, not SQLite")
            if self.paypal_base_url.rstrip("/") != sandbox_url:
                raise ValueError("Production must use the PayPal Sandbox API host")
            if self.paypal_mock_mode:
                raise ValueError("PAYPAL_MOCK_MODE cannot be enabled in production")
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
            if len(self.secret_key) < 32 or self.secret_key == DEFAULT_SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY must be a non-default secret with at least 32 characters"
                )
            if self.seed_demo_account:
                raise ValueError("SEED_DEMO_ACCOUNT cannot be enabled in production")

            def require_https_origin(name: str, value: str) -> str:
                parsed = urlsplit(value)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.query
                    or parsed.fragment
                    or parsed.path not in {"", "/"}
                    or "*" in value
                ):
                    raise ValueError(f"{name} must be an exact HTTPS origin")
                return f"{parsed.scheme}://{parsed.netloc}"

            frontend_origin = require_https_origin("FRONTEND_URL", self.frontend_url)
            backend_origin = require_https_origin("BACKEND_URL", self.backend_url)
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS must contain at least one HTTPS origin")
            cors_origins = {
                require_https_origin("CORS_ORIGINS", origin)
                for origin in self.cors_origins
            }
            if frontend_origin not in cors_origins:
                raise ValueError("CORS_ORIGINS must include FRONTEND_URL")
            if (
                frontend_origin != backend_origin
                and self.session_cookie_samesite != "none"
            ):
                raise ValueError(
                    "Cross-origin production deployments require "
                    "SESSION_COOKIE_SAMESITE=none"
                )
        if self.paypal_payouts_enabled and not self.paypal_mock_mode:
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
