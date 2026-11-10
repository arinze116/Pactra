"""Argon2id credentials, opaque sessions and CSRF enforcement."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type
from fastapi import Depends, Request, Response
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from backend.config import settings
from backend.database import get_session
from backend.errors import ApiError
from backend.models import AuthSession, DemoWorkspace, RateLimitBucket, User, utc_now


SESSION_COOKIE = "pactra_session"
CSRF_COOKIE = "pactra_csrf"
DEMO_SESSION_COOKIE = "pactra_demo_session"
DEMO_CSRF_COOKIE = "pactra_demo_csrf"
CSRF_HEADER = "X-CSRF-Token"

password_hasher = PasswordHasher(type=Type.ID)
# A fixed valid hash keeps unknown-account login timing close to known accounts.
_DUMMY_PASSWORD_HASH = password_hasher.hash("Pactra-Dummy-Password-2026!")


@dataclass(frozen=True)
class AuthContext:
    user: User
    auth_session: AuthSession
    raw_token: str
    demo_workspace: DemoWorkspace | None = None

    @property
    def is_demo(self) -> bool:
        return self.demo_workspace is not None


class FixedWindowRateLimiter:
    """Store privacy-preserving rate counters in the shared application DB."""

    def check(
        self,
        session: Session,
        key: str,
        *,
        limit: int,
        window: timedelta,
    ) -> None:
        now = utc_now()
        window_seconds = int(window.total_seconds())
        bucket_epoch = int(now.timestamp()) // window_seconds * window_seconds
        window_started_at = datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)
        expires_at = window_started_at + window
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        table = RateLimitBucket.__table__
        values = {
            "key_hash": key_hash,
            "window_started_at": window_started_at,
            "expires_at": expires_at,
            "event_count": 1,
        }
        dialect_name = session.get_bind().dialect.name
        if dialect_name == "postgresql":
            statement = postgresql_insert(table).values(**values)
        elif dialect_name == "sqlite":
            statement = sqlite_insert(table).values(**values)
        else:  # pragma: no cover - Pactra supports SQLite and PostgreSQL only.
            raise RuntimeError(f"Unsupported rate-limit database: {dialect_name}")
        statement = statement.on_conflict_do_update(
            index_elements=[table.c.key_hash],
            set_={
                "window_started_at": window_started_at,
                "expires_at": expires_at,
                "event_count": case(
                    (
                        table.c.window_started_at == window_started_at,
                        table.c.event_count + 1,
                    ),
                    else_=1,
                ),
            },
        ).returning(table.c.event_count)
        count = int(session.exec(statement).one()[0])
        session.exec(
            delete(RateLimitBucket).where(
                RateLimitBucket.expires_at < now - timedelta(days=1)
            )
        )
        session.commit()
        if count > limit:
            retry_after = max(1, int((expires_at - now).total_seconds()))
            raise ApiError(
                429,
                "RATE_LIMITED",
                "Too many requests. Try again later.",
                details={"retry_after_seconds": retry_after},
            )

    def clear(self) -> None:
        """Retain the legacy test hook; isolated test DBs start empty."""


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


def create_auth_session(
    session: Session,
    *,
    user_id: str,
    lifetime: timedelta | None = None,
) -> tuple[AuthSession, str]:
    raw_token = secrets.token_urlsafe(32)
    now = utc_now()
    session_lifetime = lifetime or timedelta(hours=settings.session_ttl_hours)
    auth_session = AuthSession(
        user_id=user_id,
        token_hash=session_token_hash(raw_token),
        created_at=now,
        expires_at=now + session_lifetime,
        last_seen_at=now,
    )
    session.add(auth_session)
    session.flush()
    return auth_session, raw_token


def _cookie_names(*, is_demo: bool) -> tuple[str, str]:
    if is_demo:
        return DEMO_SESSION_COOKIE, DEMO_CSRF_COOKIE
    return SESSION_COOKIE, CSRF_COOKIE


def set_session_cookies(
    response: Response,
    raw_token: str,
    *,
    is_demo: bool = False,
    max_age_seconds: int | None = None,
) -> None:
    session_cookie, csrf_cookie = _cookie_names(is_demo=is_demo)
    max_age = max_age_seconds or settings.session_ttl_hours * 60 * 60
    set_csrf_response_header(response, raw_token)
    response.set_cookie(
        session_cookie,
        raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    response.set_cookie(
        csrf_cookie,
        csrf_token(raw_token),
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def clear_session_cookies(response: Response, *, is_demo: bool = False) -> None:
    session_cookie, csrf_cookie = _cookie_names(is_demo=is_demo)
    response.delete_cookie(
        session_cookie,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    response.delete_cookie(
        csrf_cookie,
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


def authenticate_session_token(
    session: Session,
    *,
    raw_token: str,
    is_demo: bool,
) -> AuthContext:
    """Resolve one opaque session token for its expected principal type."""
    auth_session = session.exec(
        select(AuthSession).where(
            AuthSession.token_hash == session_token_hash(raw_token),
            AuthSession.revoked_at.is_(None),
        )
    ).one_or_none()
    now = utc_now()
    if auth_session is None:
        code = "DEMO_SESSION_EXPIRED" if is_demo else "UNAUTHENTICATED"
        message = (
            "This demo session is no longer available. Start a new demo."
            if is_demo
            else "Sign in to continue"
        )
        raise ApiError(401, code, message)
    if _as_utc(auth_session.expires_at) <= now or (
        _as_utc(auth_session.last_seen_at) + timedelta(hours=settings.session_idle_hours)
        <= now
    ):
        auth_session.revoked_at = now
        session.add(auth_session)
        session.commit()
        code = "DEMO_SESSION_EXPIRED" if is_demo else "UNAUTHENTICATED"
        message = (
            "This demo session expired. Start a new demo to continue."
            if is_demo
            else "Your session has expired. Sign in to continue."
        )
        raise ApiError(401, code, message)

    user = session.get(User, auth_session.user_id)
    if (
        user is None
        or user.status != "active"
        or bool(user.is_demo) != is_demo
    ):
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue")

    demo_workspace: DemoWorkspace | None = None
    if is_demo:
        demo_workspace = session.exec(
            select(DemoWorkspace).where(DemoWorkspace.user_id == user.id)
        ).one_or_none()
        if (
            demo_workspace is None
            or demo_workspace.status != "active"
            or _as_utc(demo_workspace.expires_at) <= now
        ):
            if demo_workspace is not None and demo_workspace.status == "active":
                demo_workspace.status = "expired"
                session.add(demo_workspace)
            auth_session.revoked_at = now
            session.add(auth_session)
            session.commit()
            raise ApiError(
                401,
                "DEMO_SESSION_EXPIRED",
                "This demo session expired. Start a new demo to continue.",
            )

    # Touch active sessions at most once every five minutes to limit writes.
    if _as_utc(auth_session.last_seen_at) + timedelta(minutes=5) <= now:
        auth_session.last_seen_at = now
        session.add(auth_session)
        session.commit()
    return AuthContext(
        user=user,
        auth_session=auth_session,
        raw_token=raw_token,
        demo_workspace=demo_workspace,
    )


def require_auth_context(
    request: Request, session: Session = Depends(get_session)
) -> AuthContext:
    demo_token = request.cookies.get(DEMO_SESSION_COOKIE)
    normal_token = request.cookies.get(SESSION_COOKIE)
    if demo_token:
        context = authenticate_session_token(
            session,
            raw_token=demo_token,
            is_demo=True,
        )
    elif normal_token:
        context = authenticate_session_token(
            session,
            raw_token=normal_token,
            is_demo=False,
        )
    else:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in to continue")
    request.state.auth = context
    return context


def require_csrf(
    request: Request,
    context: AuthContext = Depends(require_auth_context),
) -> AuthContext:
    require_same_origin(request)
    supplied = request.headers.get(CSRF_HEADER)
    cookie_value = request.cookies.get(
        DEMO_CSRF_COOKIE if context.is_demo else CSRF_COOKIE
    )
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


def login_rate_key(email: str) -> str:
    """Use an account-stable key so rotating reverse-proxy IPs cannot bypass limits."""
    email_digest = hashlib.sha256(email.encode("utf-8")).hexdigest()
    return f"login:{email_digest}"
