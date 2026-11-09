"""Production configuration must fail closed around money and persistence."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "secret_key": "production-test-secret-key-at-least-32-bytes",
        "database_url": "postgresql+psycopg://pactra:pactra@localhost/pactra",
        "frontend_url": "https://pactra-sandbox-arinze116.onrender.com",
        "backend_url": "https://pactra-sandbox-api-arinze116.onrender.com",
        "cors_origins": ["https://pactra-sandbox-arinze116.onrender.com"],
        "session_cookie_secure": True,
        "session_cookie_samesite": "none",
        "paypal_mock_mode": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_requires_postgresql() -> None:
    with pytest.raises(ValidationError, match="Production must use PostgreSQL"):
        production_settings(database_url="sqlite:///./unsafe-production.db")


def test_enabled_paypal_requires_complete_sandbox_configuration() -> None:
    with pytest.raises(ValidationError, match="client credentials"):
        production_settings(paypal_payouts_enabled=True)

    configured = production_settings(
        paypal_payouts_enabled=True,
        paypal_client_id="sandbox-client",
        paypal_client_secret="sandbox-secret",
        paypal_test_recipient_email="recipient@example.com",
    )
    assert configured.paypal_base_url == "https://api-m.sandbox.paypal.com"


def test_local_mock_mode_keeps_api_available_without_provider_credentials() -> None:
    configured = Settings(
        _env_file=None,
        app_env="development",
        paypal_payouts_enabled=True,
        paypal_mock_mode=True,
    )
    assert configured.paypal_payouts_enabled is True
    assert configured.paypal_mock_mode is True


def test_enabled_ai_requires_server_key() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        production_settings(ai_enabled=True)

    with pytest.raises(ValidationError, match="gemini-3.8-flash"):
        production_settings(
            ai_enabled=True,
            gemini_api_key="test-key",
            gemini_model="gemini-2.0-flash",
        )


def test_production_rejects_default_secret_and_unsafe_origins() -> None:
    with pytest.raises(ValidationError, match="non-default secret"):
        production_settings(secret_key="development-only-change-me-32-bytes")

    with pytest.raises(ValidationError, match="exact HTTPS origin"):
        production_settings(cors_origins=["*"])

    with pytest.raises(ValidationError, match="include FRONTEND_URL"):
        production_settings(cors_origins=["https://example.com"])


def test_cross_origin_production_requires_none_samesite() -> None:
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SAMESITE=none"):
        production_settings(session_cookie_samesite="lax")

    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE=true"):
        Settings(
            _env_file=None,
            session_cookie_samesite="none",
            session_cookie_secure=False,
        )


def test_registration_rate_limit_is_configurable_without_weakening_default() -> None:
    assert Settings(_env_file=None).auth_registration_rate_limit_per_hour == 10
    assert Settings(_env_file=None).auth_registration_global_rate_limit_per_hour == 100
    assert Settings(_env_file=None).auth_login_global_rate_limit_per_minute == 30
    assert (
        Settings(
            _env_file=None,
            auth_registration_rate_limit_per_hour=100,
        ).auth_registration_rate_limit_per_hour
        == 100
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_registration_rate_limit_per_hour=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_registration_global_rate_limit_per_hour=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_login_global_rate_limit_per_minute=0)


def test_production_can_load_secret_from_private_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "session-secret"
    secret_file.write_text("s" * 64, encoding="utf-8")
    secret_file.chmod(0o600)

    configured = production_settings(
        secret_key="",
        secret_key_file=str(secret_file),
    )

    assert configured.secret_key == "s" * 64
