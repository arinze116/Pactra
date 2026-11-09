"""Read-only verification for retained PostgreSQL backup archives."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BackupVerification:
    path: str
    passed: bool
    size_bytes: int
    age_hours: float
    sha256: str
    archive_list_valid: bool
    checks: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_checksum_file(path: Path) -> str:
    first_token = path.read_text(encoding="utf-8").strip().split(maxsplit=1)[0]
    if len(first_token) != 64 or any(
        character not in "0123456789abcdefABCDEF" for character in first_token
    ):
        raise ValueError("Checksum file does not begin with a SHA-256 digest")
    return first_token.casefold()


def verify_backup(
    path: Path,
    *,
    expected_sha256: str | None = None,
    checksum_file: Path | None = None,
    require_checksum: bool = False,
    min_size_bytes: int = 1024,
    max_age_hours: float | None = None,
    pg_restore_binary: str = "pg_restore",
    archive_timeout_seconds: float = 30,
) -> BackupVerification:
    """Verify metadata, checksum and archive readability without restoring."""
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise ValueError("Backup path must not be a symbolic link")
    resolved = expanded.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("Backup path must be a regular file")
    stat = resolved.stat()
    age_hours = max(
        0.0,
        (datetime.now(timezone.utc).timestamp() - stat.st_mtime) / 3600,
    )
    digest = sha256_file(resolved)
    checks: list[str] = []
    if stat.st_size < min_size_bytes:
        checks.append("backup_too_small")
    if max_age_hours is not None and age_hours > max_age_hours:
        checks.append("backup_stale")

    checksum = expected_sha256.casefold() if expected_sha256 else None
    if checksum_file is not None:
        expanded_checksum = checksum_file.expanduser()
        if expanded_checksum.is_symlink():
            raise ValueError("Checksum path must not be a symbolic link")
        checksum = read_checksum_file(expanded_checksum.resolve(strict=True))
    if checksum is None:
        if require_checksum:
            checks.append("checksum_missing")
    elif checksum != digest:
        checks.append("checksum_mismatch")

    archive_list_valid = False
    try:
        result = subprocess.run(
            [pg_restore_binary, "--list", str(resolved)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=archive_timeout_seconds,
        )
        archive_list_valid = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        archive_list_valid = False
    if not archive_list_valid:
        checks.append("archive_list_failed")

    return BackupVerification(
        path=str(resolved),
        passed=not checks,
        size_bytes=stat.st_size,
        age_hours=round(age_hours, 2),
        sha256=digest,
        archive_list_valid=archive_list_valid,
        checks=tuple(checks),
    )
