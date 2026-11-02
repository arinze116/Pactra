"""Async PayPal REST client with token caching and a deterministic demo mode."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx

from .config import Settings, settings
from .models import PayPalOrderResult


class PayPalError(RuntimeError):
    """A sanitized PayPal integration failure safe to surface through the API."""


class PayPalConfigurationError(PayPalError):
    """Raised when live sandbox mode is missing credentials."""


class PayPalClient:
    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self.client_id = app_settings.paypal_client_id
        self.client_secret = app_settings.paypal_client_secret
        self.base_url = app_settings.paypal_base_url.rstrip("/")
        self.mock_mode = app_settings.paypal_mock_mode
        self._token: str | None = None
        self._token_expiry: datetime | None = None
        self._token_lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=app_settings.paypal_request_timeout_seconds,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_access_token(self) -> str:
        if self.mock_mode:
            return "pactra-demo-token"

        if not self.client_id or not self.client_secret:
            raise PayPalConfigurationError(
                "PayPal credentials are required when PAYPAL_MOCK_MODE is false"
            )

        now = datetime.now(timezone.utc)
        if self._token and self._token_expiry and now < self._token_expiry:
            return self._token

        async with self._token_lock:
            now = datetime.now(timezone.utc)
            if self._token and self._token_expiry and now < self._token_expiry:
                return self._token

            try:
                response = await self._client.post(
                    "/v1/oauth2/token",
                    data={"grant_type": "client_credentials"},
                    auth=(self.client_id, self.client_secret),
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                token = payload["access_token"]
                expires_in = max(int(payload.get("expires_in", 300)) - 60, 1)
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise PayPalError("Unable to authenticate with PayPal") from exc

            self._token = token
            self._token_expiry = now + timedelta(seconds=expires_in)
            return token

    async def _headers(self, request_id: str | None = None) -> dict[str, str]:
        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        return headers

    @staticmethod
    def _money(amount: float) -> str:
        return f"{Decimal(str(amount)).quantize(Decimal('0.01')):.2f}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                path,
                json=json,
                params=params,
                headers=await self._headers(request_id),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            debug_id = exc.response.headers.get("paypal-debug-id")
            suffix = f" (debug ID: {debug_id})" if debug_id else ""
            raise PayPalError(f"PayPal rejected the request{suffix}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise PayPalError("PayPal is currently unavailable") from exc

    async def create_order(
        self,
        amount: float,
        currency: str,
        vendor: str,
        description: str,
        request_id: str | None = None,
    ) -> PayPalOrderResult:
        if self.mock_mode:
            suffix = (request_id or uuid4().hex).replace("-", "")[:12].upper()
            return PayPalOrderResult(
                order_id=f"DEMO-ORDER-{suffix}",
                status="CREATED",
                amount=amount,
                currency=currency,
            )

        payload = await self._request(
            "POST",
            "/v2/checkout/orders",
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": currency,
                            "value": self._money(amount),
                        },
                        "description": f"{vendor}: {description}"[:127],
                    }
                ],
            },
            request_id=request_id or f"pactra-order-{uuid4()}",
        )
        approve_link = next(
            (
                link.get("href")
                for link in payload.get("links", [])
                if link.get("rel") == "approve"
            ),
            None,
        )
        return PayPalOrderResult(
            order_id=payload["id"],
            status=payload.get("status", "CREATED"),
            amount=amount,
            currency=currency,
            approve_link=approve_link,
        )

    async def capture_order(
        self, order_id: str, request_id: str | None = None
    ) -> PayPalOrderResult:
        if self.mock_mode:
            return PayPalOrderResult(
                order_id=order_id,
                status="COMPLETED",
                amount=0.0,
                currency="USD",
            )

        payload = await self._request(
            "POST",
            f"/v2/checkout/orders/{order_id}/capture",
            json={},
            request_id=request_id or f"pactra-capture-{order_id}",
        )
        purchase_unit = (payload.get("purchase_units") or [{}])[0]
        captures = purchase_unit.get("payments", {}).get("captures", [])
        capture_amount = captures[0].get("amount", {}) if captures else {}
        return PayPalOrderResult(
            order_id=payload.get("id", order_id),
            status=payload.get("status", "FAILED"),
            amount=float(capture_amount.get("value", 0)),
            currency=capture_amount.get("currency_code", "USD"),
        )

    async def send_payout(
        self,
        recipient_email: str,
        amount: float,
        currency: str,
        note: str,
        request_id: str | None = None,
    ) -> dict[str, str]:
        if self.mock_mode:
            suffix = (request_id or uuid4().hex).replace("-", "")[:12].upper()
            return {
                "batch_id": f"DEMO-PAYOUT-{suffix}",
                "batch_status": "SUCCESS",
            }

        batch_id = (request_id or f"pactra-{uuid4()}")[:50]
        payload = await self._request(
            "POST",
            "/v1/payments/payouts",
            json={
                "sender_batch_header": {
                    "sender_batch_id": batch_id,
                    "email_subject": "You have received a payment from Pactra",
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "amount": {
                            "value": self._money(amount),
                            "currency": currency,
                        },
                        "receiver": recipient_email,
                        "note": note[:4000],
                    }
                ],
            },
            request_id=request_id or batch_id,
        )
        header = payload.get("batch_header", {})
        return {
            "batch_id": header.get("payout_batch_id", batch_id),
            "batch_status": header.get("batch_status", "PENDING"),
        }

    async def get_transaction_history(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        if self.mock_mode:
            return []
        payload = await self._request(
            "GET",
            "/v1/reporting/transactions",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "fields": "all",
                "page_size": 100,
            },
        )
        return payload.get("transaction_details", [])
