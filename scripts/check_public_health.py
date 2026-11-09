#!/usr/bin/env python3
"""Check Pactra public liveness and readiness with bounded requests."""

from __future__ import annotations

import argparse
import json

from backend.diagnostics.http_health import (
    check_endpoint,
    check_frontend,
    validate_base_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Pactra health endpoints.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=10)
    parser.add_argument("--max-latency-ms", type=int, default=5_000)
    parser.add_argument("--allow-http", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = validate_base_url(args.base_url, allow_http=args.allow_http)
    results = [
        check_frontend(
            base_url,
            timeout_seconds=args.timeout_seconds,
            max_latency_ms=args.max_latency_ms,
        ),
        *[
            check_endpoint(
                base_url,
                path,
                timeout_seconds=args.timeout_seconds,
                max_latency_ms=args.max_latency_ms,
            )
            for path in ("/api/health", "/api/ready")
        ],
    ]
    passed = all(result.passed for result in results)
    payload = {
        "base_url": base_url,
        "passed": passed,
        "checks": [result.as_dict() for result in results],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for result in results:
            print(
                f"{'PASS' if result.passed else 'FAIL'} path={result.path} "
                f"status={result.status_code} latency_ms={result.latency_ms} "
                f"classification={result.classification}"
            )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
