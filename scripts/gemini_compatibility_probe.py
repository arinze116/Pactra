#!/usr/bin/env python3
"""Probe Pactra's Gemini function-call contract without executing a tool."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


PROBE_MESSAGE = (
    "Create an internal sandbox vendor payment to Linear for $49 USD in "
    "category software, reason monthly software subscription. Use the payment "
    "creation tool now."
)
EXPECTED_FUNCTION = "create_payment_request"
EXPECTED_ARGUMENTS = {
    "type": "vendor_payment",
    "vendor": "Linear",
    "amount_cents": 4_900,
    "currency": "USD",
    "category": "software",
    "rail": "internal_sandbox",
}
TOOL_ARGUMENT_KEYS = {
    "type",
    "vendor",
    "recipient",
    "amount_cents",
    "currency",
    "category",
    "reason",
    "rail",
}
TOOL_REQUIRED_KEYS = TOOL_ARGUMENT_KEYS - {"recipient"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=2, choices=(1, 2))
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    parser.add_argument(
        "--round-trip",
        action="store_true",
        help="Send a synthetic function response and require a safe text follow-up.",
    )
    return parser.parse_args()


def _load_api_key(env_file: Path) -> str:
    values = dotenv_values(env_file)
    api_key = values.get("GEMINI_API_KEY")
    if not isinstance(api_key, str) or not api_key.strip():
        raise RuntimeError("GEMINI_API_KEY is missing from the supplied environment file")
    return api_key.strip()


def _safe_error_message(exc: Exception, api_key: str) -> str:
    message = " ".join(str(exc).split())
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    return message[:500]


def _classify_error(exc: Exception) -> tuple[str, int | None, str | None]:
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    numeric_code = code if isinstance(code, int) else None
    status_name = str(status) if status is not None else None
    if isinstance(exc, TimeoutError):
        return "timeout", numeric_code, status_name
    if numeric_code in {401, 403}:
        return "authentication_or_permission", numeric_code, status_name
    if numeric_code == 404:
        return "model_unavailable_or_inaccessible", numeric_code, status_name
    if numeric_code == 429:
        return "rate_limit_or_quota", numeric_code, status_name
    if numeric_code in {500, 502, 503, 504}:
        return "provider_capacity", numeric_code, status_name
    if numeric_code == 400:
        return "request_or_schema_incompatibility", numeric_code, status_name
    return "application_or_sdk_error", numeric_code, status_name


def _validate_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    from backend.schemas import PaymentRequest

    missing = sorted(TOOL_REQUIRED_KEYS - arguments.keys())
    extras = sorted(arguments.keys() - TOOL_ARGUMENT_KEYS)
    if missing:
        raise ValueError(f"missing required arguments: {', '.join(missing)}")
    if extras:
        raise ValueError(f"unexpected arguments: {', '.join(extras)}")
    request = PaymentRequest.model_validate(
        {**arguments, "idempotency_key": "gemini-compatibility-probe-0001"}
    )
    validated = request.model_dump(mode="json", exclude={"idempotency_key"})
    for name, expected in EXPECTED_ARGUMENTS.items():
        actual = validated.get(name)
        if name == "vendor" and isinstance(actual, str):
            if actual.casefold() == str(expected).casefold():
                continue
        if actual != expected:
            raise ValueError(
                f"argument {name!r} was {actual!r}; expected {expected!r}"
            )
    return validated


def _verify_rejection_guards() -> dict[str, bool]:
    valid = {
        **EXPECTED_ARGUMENTS,
        "recipient": None,
        "reason": "Monthly software subscription",
    }
    malformed = {**valid, "currency": "EUR"}
    missing = {key: value for key, value in valid.items() if key != "amount_cents"}
    extra = {**valid, "user_id": "00000000-0000-4000-8000-000000000000"}
    results: dict[str, bool] = {}
    for name, value in (
        ("malformed_arguments_rejected", malformed),
        ("missing_arguments_rejected", missing),
        ("extra_arguments_rejected", extra),
    ):
        try:
            _validate_arguments(value)
        except (TypeError, ValueError):
            results[name] = True
        else:
            results[name] = False
    return results


async def _probe_once(
    *,
    model: str,
    api_key: str,
    timeout_seconds: float,
    attempt: int,
    round_trip: bool,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    from backend.services.assistant import SYSTEM_PROMPT, TOOLS

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=PROBE_MESSAGE)],
        )
    ]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.0,
        max_output_tokens=2000,
    )
    started = time.monotonic()
    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            ),
            timeout=timeout_seconds,
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        candidates = response.candidates or []
        candidate = candidates[0] if candidates else None
        finish_reason = getattr(candidate, "finish_reason", None)
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        calls = [part.function_call for part in parts if part.function_call]
        response_kind = "function_call" if calls else "text_or_empty"
        result: dict[str, Any] = {
            "attempt": attempt,
            "provider_status": "success",
            "latency_ms": latency_ms,
            "finish_reason": str(finish_reason) if finish_reason is not None else None,
            "response_kind": response_kind,
            "function_call_count": len(calls),
            "passed": False,
        }
        if len(calls) != 1:
            result["validation_error"] = (
                f"expected one genuine function call; received {len(calls)}"
            )
            return result
        call = calls[0]
        function_name = str(call.name or "")
        arguments = dict(call.args or {})
        result["function_name"] = function_name
        result["arguments"] = arguments
        if function_name != EXPECTED_FUNCTION:
            result["validation_error"] = (
                f"expected function {EXPECTED_FUNCTION!r}; received {function_name!r}"
            )
            return result
        try:
            result["validated_arguments"] = _validate_arguments(arguments)
        except (TypeError, ValueError) as exc:
            result["validation_error"] = str(exc)
            return result
        if round_trip:
            from backend.services.assistant import _function_response_part

            contents.append(content)
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        _function_response_part(
                            call,
                            name=function_name,
                            response={
                                "id": "00000000-0000-4000-8000-000000000001",
                                "status": "completed",
                                "vendor": "Linear",
                                "amount_cents": 4_900,
                                "currency": "USD",
                                "category": "software",
                                "rail": "internal_sandbox",
                                "failure_code": None,
                            },
                        )
                    ],
                )
            )
            follow_up_started = time.monotonic()
            try:
                follow_up = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config,
                    ),
                    timeout=timeout_seconds,
                )
            except Exception as exc:
                classification, code, status = _classify_error(exc)
                result["round_trip"] = {
                    "provider_status": "error",
                    "latency_ms": round(
                        (time.monotonic() - follow_up_started) * 1000
                    ),
                    "error_classification": classification,
                    "http_code": code,
                    "provider_status_name": status,
                    "exception_type": type(exc).__name__,
                    "error_detail": _safe_error_message(exc, api_key),
                }
                return result
            follow_up_candidate = (follow_up.candidates or [None])[0]
            follow_up_content = getattr(follow_up_candidate, "content", None)
            follow_up_parts = getattr(follow_up_content, "parts", None) or []
            follow_up_calls = [
                part.function_call for part in follow_up_parts if part.function_call
            ]
            follow_up_text = (follow_up.text or "").strip()
            result["round_trip"] = {
                "provider_status": "success",
                "latency_ms": round((time.monotonic() - follow_up_started) * 1000),
                "finish_reason": str(
                    getattr(follow_up_candidate, "finish_reason", None)
                ),
                "function_call_count": len(follow_up_calls),
                "text_present": bool(follow_up_text),
            }
            if follow_up_calls or not follow_up_text:
                result["validation_error"] = (
                    "function-response round trip did not produce a final text reply"
                )
                return result
        result["passed"] = True
        return result
    except Exception as exc:
        latency_ms = round((time.monotonic() - started) * 1000)
        classification, code, status = _classify_error(exc)
        return {
            "attempt": attempt,
            "provider_status": "error",
            "latency_ms": latency_ms,
            "error_classification": classification,
            "http_code": code,
            "provider_status_name": status,
            "exception_type": type(exc).__name__,
            "error_detail": _safe_error_message(exc, api_key),
            "passed": False,
        }
    finally:
        try:
            await client.aio.aclose()
        except Exception:
            pass


async def _main() -> int:
    args = _parse_args()
    api_key = _load_api_key(args.env_file)
    os.environ["AI_ENABLED"] = "false"
    os.environ["GEMINI_API_KEY"] = api_key
    results = []
    for attempt in range(1, args.attempts + 1):
        results.append(
            await _probe_once(
                model=args.model,
                api_key=api_key,
                timeout_seconds=args.timeout_seconds,
                attempt=attempt,
                round_trip=args.round_trip,
            )
        )
    rejection_guards = _verify_rejection_guards()
    passed = all(result["passed"] for result in results) and all(
        rejection_guards.values()
    )
    print(
        json.dumps(
            {
                "model": args.model,
                "sdk": "google-genai==2.23.0",
                "api_version": "v1beta",
                "timeout_seconds": args.timeout_seconds,
                "attempts": results,
                "local_validation": rejection_guards,
                "passed": passed,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
