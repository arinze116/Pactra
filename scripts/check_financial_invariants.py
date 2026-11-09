#!/usr/bin/env python3
"""Run Pactra's read-only financial invariant diagnostics."""

from __future__ import annotations

import argparse
import json

from sqlalchemy import text
from sqlmodel import Session

from backend.database import engine
from backend.diagnostics.invariants import collect_financial_invariants


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Pactra financial invariants without modifying data."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with Session(engine) as session:
        if engine.dialect.name == "postgresql":
            session.exec(text("SET TRANSACTION READ ONLY"))
        elif engine.dialect.name == "sqlite":
            session.exec(text("PRAGMA query_only=ON"))
        report = collect_financial_invariants(session)
        session.rollback()
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        for check in report.checks:
            status = "PASS" if check.passed else "FAIL"
            print(
                f"{status} {check.severity} {check.code} "
                f"violations={check.violation_count}"
            )
        print(f"overall={'PASS' if report.passed else 'FAIL'}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
