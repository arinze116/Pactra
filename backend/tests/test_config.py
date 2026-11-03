"""Production configuration must fail closed around money and persistence."""

import pytest
from pydantic import ValidationError

from backend.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "secret_key": "production-test-secret-key-at-least-32-bytes",
        "database_url": "postgresql+psycopg://pactra:pactra@localhost/pactra",
        "session_cookie_secure": True,
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


def test_enabled_ai_requires_server_key() -> None:
    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        production_settings(ai_enabled=True)

    with pytest.raises(ValidationError, match="gemini-3.8-flash"):
        production_settings(
            ai_enabled=True,
            gemini_api_key="test-key",
            gemini_model="gemini-2.0-flash",
        )
