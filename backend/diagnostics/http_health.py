"""Bounded, privacy-safe HTTP health checks."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class EndpointHealth:
    path: str
    passed: bool
    status_code: int | None
    latency_ms: int
    classification: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_base_url(base_url: str, *, allow_http: bool = False) -> str:
    parsed = urlsplit(base_url.strip().rstrip("/"))
    allowed_schemes = {"https", "http"} if allow_http else {"https"}
    if (
        parsed.scheme not in allowed_schemes
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Base URL must be an exact HTTP(S) origin without credentials")
    return f"{parsed.scheme}://{parsed.netloc}"


def check_endpoint(
    base_url: str,
    path: str,
    *,
    timeout_seconds: float = 10,
    max_latency_ms: int = 5_000,
) -> EndpointHealth:
    """Check one safe JSON health endpoint without returning its body."""
    started = time.monotonic()
    status_code: int | None = None
    classification = "unknown"
    passed = False
    try:
        request = Request(
            f"{base_url}{path}",
            headers={"Accept": "application/json", "User-Agent": "Pactra-health-monitor/1.0"},
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = response.status
            payload = json.loads(response.read(16_384).decode("utf-8"))
        if path == "/api/health":
            valid_payload = payload.get("status") == "ok"
        elif path == "/api/ready":
            valid_payload = (
                payload.get("status") == "ready"
                and payload.get("database") == "ok"
                and payload.get("sandbox_mode") is True
                and payload.get("internal_sandbox_available") is True
            )
        else:
            valid_payload = isinstance(payload, dict) and bool(payload.get("status"))
        classification = "ok" if valid_payload else "invalid_payload"
        passed = status_code == 200 and valid_payload
    except HTTPError as exc:
        status_code = exc.code
        classification = "http_error"
    except TimeoutError:
        classification = "timeout"
    except (URLError, OSError):
        classification = "network_error"
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
        classification = "invalid_payload"
    latency_ms = round((time.monotonic() - started) * 1000)
    if latency_ms > max_latency_ms:
        passed = False
        classification = "latency_budget_exceeded"
    return EndpointHealth(
        path=path,
        passed=passed,
        status_code=status_code,
        latency_ms=latency_ms,
        classification=classification,
    )


def check_frontend(
    base_url: str,
    *,
    timeout_seconds: float = 10,
    max_latency_ms: int = 5_000,
) -> EndpointHealth:
    """Check the public shell without retaining or emitting its HTML."""
    started = time.monotonic()
    status_code: int | None = None
    classification = "unknown"
    passed = False
    try:
        request = Request(
            f"{base_url}/",
            headers={"Accept": "text/html", "User-Agent": "Pactra-health-monitor/1.0"},
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = response.status
            content_type = response.headers.get_content_type()
            body = response.read(65_536).decode("utf-8", errors="replace")
        valid_payload = content_type == "text/html" and "Pactra" in body
        classification = "ok" if valid_payload else "invalid_payload"
        passed = status_code == 200 and valid_payload
    except HTTPError as exc:
        status_code = exc.code
        classification = "http_error"
    except TimeoutError:
        classification = "timeout"
    except (URLError, OSError):
        classification = "network_error"
    latency_ms = round((time.monotonic() - started) * 1000)
    if latency_ms > max_latency_ms:
        passed = False
        classification = "latency_budget_exceeded"
    return EndpointHealth(
        path="/",
        passed=passed,
        status_code=status_code,
        latency_ms=latency_ms,
        classification=classification,
    )
