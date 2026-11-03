"""FastAPI application exposing Pactra's agent and governance dashboard APIs."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from .agent import PactraAgent
from .auth import (
    AuthContext,
    auth_rate_limiter,
    clear_session_cookies,
    client_ip,
    create_auth_session,
    hash_password,
    login_rate_key,
    require_auth_context,
    require_csrf,
    require_same_origin,
    set_session_cookies,
    session_token_hash,
    verify_password,
)
from .config import settings
from .database import create_db_and_tables, get_session
from .defaults import INITIAL_SANDBOX_CENTS
from .errors import ApiError
from .models import AuthSession, ChatRequest, ChatResponse, SpendSummary, Transaction, User
from .paypal_client import PayPalClient
from .policy_engine import PolicyConfigurationError, PolicyEngine
from .schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LedgerItemResponse,
    LedgerPageResponse,
    LoginRequest,
    RegistrationRequest,
    RegistrationResponse,
    TopUpRequest,
    TopUpResponse,
    UserResponse,
    WalletBalanceResponse,
)
from .services.accounts import EmailAlreadyExists, create_account
from .services.audit import record_audit_event
from .services.ledger import (
    IdempotencyConflict,
    LedgerError,
    TopUpLimitReached,
    get_wallet_for_user,
    list_wallet_ledger,
    top_up_wallet,
    wallet_balance,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    try:
        app.state.policy_engine = PolicyEngine(settings.resolved_policy_path)
    except PolicyConfigurationError:
        logger.exception("Pactra could not load its policy")
        raise
    app.state.paypal_client = PayPalClient()
    app.state.agent = PactraAgent()
    logger.info("Pactra API started (PayPal mock mode: %s)", settings.paypal_mock_mode)
    try:
        yield
    finally:
        await app.state.paypal_client.close()


app = FastAPI(
    title="Pactra API",
    description="AI agent payment governance for PayPal",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_and_security_headers(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Check the submitted fields and try again.",
                "request_id": request.state.request_id,
            }
        },
    )

SessionDependency = Annotated[Session, Depends(get_session)]
AuthDependency = Annotated[AuthContext, Depends(require_auth_context)]
MutationAuthDependency = Annotated[AuthContext, Depends(require_csrf)]


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email)


def _balance_response(balance: Any) -> WalletBalanceResponse:
    return WalletBalanceResponse(
        currency=balance.currency,
        available_cents=balance.available_cents,
        reserved_cents=balance.reserved_cents,
        posted_cents=balance.posted_cents,
        sandbox_generation=balance.sandbox_generation,
    )


@app.post(
    "/api/auth/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_same_origin)],
)
def register(
    payload: RegistrationRequest,
    request: Request,
    response: Response,
    db_session: SessionDependency,
) -> RegistrationResponse:
    auth_rate_limiter.check(
        f"register:{client_ip(request)}", limit=10, window=timedelta(hours=1)
    )
    try:
        bootstrap = create_account(
            db_session,
            email=str(payload.email),
            password_hash=hash_password(payload.password),
        )
    except EmailAlreadyExists as exc:
        raise ApiError(409, "EMAIL_EXISTS", "An account with this email already exists") from exc

    _, raw_token = create_auth_session(db_session, user_id=bootstrap.user.id)
    db_session.commit()
    set_session_cookies(response, raw_token)
    return RegistrationResponse(
        user=_user_response(bootstrap.user),
        wallet=_balance_response(bootstrap.balance),
        sandbox_funds_cents=INITIAL_SANDBOX_CENTS,
        message="Account created. Your sandbox wallet is ready.",
    )


@app.post(
    "/api/auth/login",
    response_model=AuthResponse,
    dependencies=[Depends(require_same_origin)],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db_session: SessionDependency,
) -> AuthResponse:
    auth_rate_limiter.check(
        login_rate_key(request, str(payload.email)),
        limit=5,
        window=timedelta(minutes=15),
    )
    user = db_session.exec(select(User).where(User.email == str(payload.email))).one_or_none()
    if user is None or user.status != "active" or not verify_password(
        payload.password, user.password_hash if user else None
    ):
        if user is not None:
            record_audit_event(
                db_session,
                user_id=user.id,
                actor_type="user",
                actor_id=user.id,
                entity_type="user",
                entity_id=user.id,
                event_type="auth.login_failed",
                payload={},
            )
            db_session.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")

    old_raw_token = request.cookies.get("pactra_session")
    if old_raw_token:
        old_session = db_session.exec(
            select(AuthSession).where(
                AuthSession.token_hash == session_token_hash(old_raw_token),
                AuthSession.revoked_at.is_(None),
            )
        ).one_or_none()
        if old_session is not None:
            old_session.revoked_at = datetime.now(timezone.utc)
            db_session.add(old_session)

    _, raw_token = create_auth_session(db_session, user_id=user.id)
    record_audit_event(
        db_session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
        event_type="auth.login_succeeded",
        payload={},
    )
    db_session.commit()
    set_session_cookies(response, raw_token)
    return AuthResponse(user=_user_response(user))


@app.get("/api/auth/me", response_model=AuthResponse)
def current_user(context: AuthDependency) -> AuthResponse:
    return AuthResponse(user=_user_response(context.user))


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> Response:
    context.auth_session.revoked_at = datetime.now(timezone.utc)
    db_session.add(context.auth_session)
    record_audit_event(
        db_session,
        user_id=context.user.id,
        actor_type="user",
        actor_id=context.user.id,
        entity_type="user",
        entity_id=context.user.id,
        event_type="auth.logout",
        payload={},
    )
    db_session.commit()
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.post("/api/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> Response:
    if not verify_password(payload.current_password, context.user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Current password is incorrect.")
    if verify_password(payload.new_password, context.user.password_hash):
        raise ApiError(400, "PASSWORD_UNCHANGED", "Choose a different password.")

    now = datetime.now(timezone.utc)
    active_sessions = db_session.exec(
        select(AuthSession).where(
            AuthSession.user_id == context.user.id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    for active_session in active_sessions:
        active_session.revoked_at = now
        db_session.add(active_session)
    context.user.password_hash = hash_password(payload.new_password)
    db_session.add(context.user)
    _, raw_token = create_auth_session(db_session, user_id=context.user.id)
    record_audit_event(
        db_session,
        user_id=context.user.id,
        actor_type="user",
        actor_id=context.user.id,
        entity_type="user",
        entity_id=context.user.id,
        event_type="auth.password_changed",
        payload={},
    )
    db_session.commit()
    set_session_cookies(response, raw_token)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.get("/api/wallet", response_model=WalletBalanceResponse)
def get_wallet(context: AuthDependency, db_session: SessionDependency) -> WalletBalanceResponse:
    wallet = get_wallet_for_user(db_session, context.user.id)
    return _balance_response(wallet_balance(db_session, wallet))


@app.post(
    "/api/wallet/topups",
    response_model=TopUpResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_wallet_topup(
    payload: TopUpRequest,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> TopUpResponse:
    try:
        journal, balance = top_up_wallet(
            db_session,
            user_id=context.user.id,
            amount_cents=payload.amount_cents,
            idempotency_key=payload.idempotency_key,
        )
        db_session.commit()
    except IdempotencyConflict as exc:
        db_session.rollback()
        raise ApiError(409, "IDEMPOTENCY_CONFLICT", str(exc)) from exc
    except TopUpLimitReached as exc:
        db_session.rollback()
        raise ApiError(429, "RATE_LIMITED", str(exc)) from exc
    except LedgerError as exc:
        db_session.rollback()
        raise ApiError(400, "INVALID_TOPUP", str(exc)) from exc
    return TopUpResponse(
        topup_id=journal.id,
        amount_cents=payload.amount_cents,
        balance=_balance_response(balance),
        message="Test funds added",
    )


@app.get("/api/wallet/ledger", response_model=LedgerPageResponse)
def get_wallet_ledger(
    context: AuthDependency,
    db_session: SessionDependency,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> LedgerPageResponse:
    try:
        items, next_cursor = list_wallet_ledger(
            db_session,
            user_id=context.user.id,
            cursor=cursor,
            limit=limit,
        )
    except LedgerError as exc:
        raise ApiError(400, "INVALID_CURSOR", str(exc)) from exc
    return LedgerPageResponse(
        items=[
            LedgerItemResponse(
                journal_id=item.journal_id,
                journal_type=item.journal_type,
                transaction_id=item.transaction_id,
                wallet_delta_cents=item.wallet_delta_cents,
                counter_account_label=item.counter_account_label,
                created_at=item.created_at,
            )
            for item in items
        ],
        next_cursor=next_cursor,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    _context: MutationAuthDependency,
    db_session: SessionDependency,
) -> ChatResponse:
    # The legacy agent mutates a global demo table. Keep it unreachable until
    # the unified owner-scoped transaction service replaces this route.
    raise ApiError(
        503,
        "PAYMENT_SERVICE_UPGRADING",
        "The governed payment service is not available yet.",
    )


@app.get("/api/transactions", response_model=list[Transaction])
def list_transactions(
    db_session: SessionDependency,
    _context: AuthDependency,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(approved|blocked|pending_approval)$")
    ] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 50,
) -> list[Transaction]:
    raise ApiError(
        503,
        "PAYMENT_SERVICE_UPGRADING",
        "The governed payment service is not available yet.",
    )


@app.get("/api/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(
    transaction_id: str, db_session: SessionDependency, _context: AuthDependency
) -> Transaction:
    raise ApiError(
        503,
        "PAYMENT_SERVICE_UPGRADING",
        "The governed payment service is not available yet.",
    )


@app.get("/api/spend-summary", response_model=list[SpendSummary])
def spend_summary(
    request: Request, db_session: SessionDependency, _context: AuthDependency
) -> list[SpendSummary]:
    raise ApiError(
        503,
        "PAYMENT_SERVICE_UPGRADING",
        "The governed payment service is not available yet.",
    )


@app.get("/api/policy", response_model=dict[str, Any])
def get_policy(request: Request, _context: AuthDependency) -> dict[str, Any]:
    raise ApiError(
        503,
        "POLICY_SERVICE_UPGRADING",
        "The account policy service is not available yet.",
    )


@app.post(
    "/api/policy/approve/{transaction_id}",
    response_model=Transaction,
)
async def approve_transaction(
    transaction_id: str,
    request: Request,
    _context: MutationAuthDependency,
    db_session: SessionDependency,
) -> Transaction:
    raise ApiError(
        503,
        "PAYMENT_SERVICE_UPGRADING",
        "The governed payment service is not available yet.",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
