#!/usr/bin/env python3
"""Seed, inspect or safely reset Pactra's isolated SQLite demo database."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, select

from backend.config import PROJECT_ROOT, settings
from backend.demo_data import (
    DEMO_EMAIL,
    seed_demo_dataset,
    validated_demo_database_path,
    verify_demo_schema,
)
from backend.models import AuditEvent, PaymentTransaction, User


SEED_CONFIRMATION = "SEED_PACTRA_DEMO"
RESET_CONFIRMATION = "RESET_PACTRA_DEMO"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage an explicitly isolated Pactra demo database."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, confirmation in (
        ("seed", SEED_CONFIRMATION),
        ("reset", RESET_CONFIRMATION),
    ):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--confirm",
            required=True,
            help=f"Required exact value: {confirmation}",
        )
    subparsers.add_parser("status")
    return parser.parse_args()


def _assert_confirmation(command: str, supplied: str) -> None:
    expected = SEED_CONFIRMATION if command == "seed" else RESET_CONFIRMATION
    if supplied != expected:
        raise RuntimeError(f"{command} requires --confirm {expected}")


def _existing_user_emails(path: Path) -> list[str]:
    if not path.exists():
        return []
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if table is None:
            return []
        return [row[0] for row in connection.execute("SELECT email FROM users")]
    finally:
        connection.close()


def assert_resettable_database(path: Path) -> None:
    unexpected = [email for email in _existing_user_emails(path) if email != DEMO_EMAIL]
    if unexpected:
        raise RuntimeError("Demo reset refused because non-demo users exist")


def _remove_demo_database(path: Path) -> None:
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink():
                raise RuntimeError("Demo reset refused a symbolic-link database file")
            candidate.unlink()


def _migrate_demo_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=os.environ.copy(),
        check=True,
    )


def _seed() -> dict[str, object]:
    from backend.database import engine

    verify_demo_schema(engine)
    with Session(engine, expire_on_commit=False) as session:
        return seed_demo_dataset(session).as_dict()


def _status() -> dict[str, object]:
    from backend.database import engine

    verify_demo_schema(engine)
    with Session(engine) as session:
        user_count = int(session.exec(select(func.count(User.id))).one())
        transaction_count = int(
            session.exec(select(func.count(PaymentTransaction.id))).one()
        )
        marker_count = int(
            session.exec(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.event_type == "demo.dataset_seeded"
                )
            ).one()
        )
    return {
        "ready": user_count == 1 and marker_count == 1,
        "user_count": user_count,
        "transaction_count": transaction_count,
        "dataset_marker_count": marker_count,
    }


def main() -> int:
    args = parse_args()
    path = validated_demo_database_path(settings.database_url, settings.app_env)
    if args.command == "reset":
        _assert_confirmation(args.command, args.confirm)
        assert_resettable_database(path)
        from backend.database import engine

        engine.dispose()
        _remove_demo_database(path)
        _migrate_demo_database(path)
        payload = {"reset": True, "dataset": _seed()}
    elif args.command == "seed":
        _assert_confirmation(args.command, args.confirm)
        payload = {"reset": False, "dataset": _seed()}
    else:
        payload = _status()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
