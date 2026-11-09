#!/usr/bin/env python3
"""Verify a PostgreSQL custom-format backup without restoring it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.diagnostics.backups import verify_backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check backup age, size, SHA-256 and pg_restore readability."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--checksum-file", type=Path)
    parser.add_argument("--require-checksum", action="store_true")
    parser.add_argument("--min-bytes", type=int, default=1024)
    parser.add_argument("--max-age-hours", type=float)
    parser.add_argument("--pg-restore", default="pg_restore")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = verify_backup(
        args.archive,
        expected_sha256=args.sha256,
        checksum_file=args.checksum_file,
        require_checksum=args.require_checksum,
        min_size_bytes=args.min_bytes,
        max_age_hours=args.max_age_hours,
        pg_restore_binary=args.pg_restore,
    )
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"status={'PASS' if report.passed else 'FAIL'}")
        print(f"path={report.path}")
        print(f"size_bytes={report.size_bytes}")
        print(f"age_hours={report.age_hours}")
        print(f"sha256={report.sha256}")
        print(f"archive_list_valid={str(report.archive_list_valid).lower()}")
        print(f"checks={','.join(report.checks) if report.checks else 'none'}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
