"""Argon2id credentials, opaque sessions and CSRF enforcement."""

import hashlib
import hmac
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type
from fastapi import Depends, Request, Response
from sqlmodel import Session, select

from backend.config import settings
from backend.database import get_session
from backend.errors import ApiError
from backend.models import AuthSession, User, utc_now


SESSION_COOKIE = "pactra_session"
CSRF_COOKIE = "pactra_csrf"
CSRF_HEADER = "X-CSRF-Token"

password_hasher = PasswordHasher(type=Type.ID)
# A fixed valid hash keeps unknown-account login timing close to known accounts.
_DUMMY_PASSWORD_HASH = password_hasher.hash("Pactra-Dummy-Password-2026!")


@dataclass(frozen=True)
class AuthContext:
    user: User
    auth_session: AuthSession
    raw_token: str


class FixedWindowRateLimiter:
    """Small in-process limiter for public auth endpoints.

    Deployment remains single-instance for the hackathon; durable financial
    limits are enforced in PostgreSQL rather than this process-local helper.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window: timedelta) -> None:
        now = utc_now()
        threshold = now - window
        with self._lock:
            events = self._events[key]
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= limit:
                raise ApiError(429, "RATE_LIMITED", "Too many requests. Try again later.")
            events.append(now)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


auth_rate_limiter = FixedWindowRateLimiter()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    candidate_hash = password_hash or _DUMMY_PASSWORD_HASH
    try:
        return password_hasher.verify(candidate_hash, password) and password_hash is not None
    except (InvalidHashError, VerifyMismatchError):
        return False


def session_token_hash(raw_token: str) -> bytes:
    return hashlib.sha256(raw_token.encode("utf-8")).digest()


def csrf_token(raw_token: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        f"csrf:{raw_token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def set_csrf_response_header(response: Response, raw_token: str) -> None:
    """Expose the synchronizer token without exposing the session cookie."""
    response.headers[CSRF_HEADER] = csrf_token(raw_token)


def create_auth_session(session: Session, *, user_id: str) -> tuple[AuthSession, str]:
    raw_token = secrets.token_urlsafe(32)
    now = utc_now()
    auth_session = AuthSession(
        user_id=user_id,
        token_hash=session_token_hash(raw_token),
        created_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        last_seen_at=now,
    )
    session.add(auth_session)
    session.flush()
    return auth_session, raw_token


def set_session_cookies(response: Response, raw_token: str) -> None:
    max_age = settings.session_ttl_hours * 60 * 60
    set_csrf_response_header(response, raw_token)
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token(raw_token),
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    response.delete_cookie(
        CSRF_COOKIE,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def require_same_origin(request: Request) -> None:
    """Reject cross-site browser mutations before credential processing."""
    source = request.headers.get("origin")
    if source is None:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlsplit(referer)
            source = f"{parsed.scheme}://{parsed.netloc}"
    if source is None:
        raise ApiError(403, "ORIGIN_REQUIRED", "A same-origin request is required")

    request_origin = str(request.base_url).rstrip("/")
    allowed = {
        request_origin,
        settings.frontend_url.rstrip("/"),
        settings.backend_url.rstrip("/"),
        *(origin.rstrip("/") for origin in settings.cors_origins),
    }
    if source.rstrip("/") not in allowed:
        raise ApiError(403, "ORIGIN_MISMATCH", "Cross-origin request rejected")


def require_auth_context(
    request: Request, session: Session = Depends(get_session)
) -> AuthContext:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue")

    auth_session = session.exec(
        select(AuthSession).where(
            AuthSession.token_hash == session_token_hash(raw_token),
            AuthSession.revoked_at.is_(None),
        )
    ).one_or_none()
    now = utc_now()
    if auth_session is None:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue")
    if _as_utc(auth_session.expires_at) <= now or (
        _as_utc(auth_session.last_seen_at) + timedelta(hours=settings.session_idle_hours)
        <= now
    ):
        auth_session.revoked_at = now
        session.add(auth_session)
        session.commit()
        raise ApiError(401, "UNAUTHENTICATED", "Your session has expired. Sign in to continue.")

    user = session.get(User, auth_session.user_id)
    if user is None or user.status != "active":
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue")

    # Touch active sessions at most once every five minutes to limit writes.
    if _as_utc(auth_session.last_seen_at) + timedelta(minutes=5) <= now:
        auth_session.last_seen_at = now
        session.add(auth_session)
        session.commit()
    context = AuthContext(user=user, auth_session=auth_session, raw_token=raw_token)
    request.state.auth = context
    return context


def require_csrf(
    request: Request,
    context: AuthContext = Depends(require_auth_context),
) -> AuthContext:
    require_same_origin(request)
    supplied = request.headers.get(CSRF_HEADER)
    cookie_value = request.cookies.get(CSRF_COOKIE)
    expected = csrf_token(context.raw_token)
    if (
        supplied is None
        or cookie_value is None
        or not hmac.compare_digest(supplied, expected)
        or not hmac.compare_digest(cookie_value, expected)
    ):
        raise ApiError(403, "CSRF_INVALID", "Security token is missing or invalid")
    return context


def client_ip(request: Request) -> str:
    # Trusted proxy configuration is handled by the deployment server.
    return request.client.host if request.client else "unknown"


def login_rate_key(request: Request, email: str) -> str:
    email_digest = hashlib.sha256(email.encode("utf-8")).hexdigest()
    return f"login:{client_ip(request)}:{email_digest}"

