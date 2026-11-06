"""FastAPI application exposing Pactra's agent and governance dashboard APIs."""

import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import Session, select

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
    set_csrf_response_header,
    set_session_cookies,
    session_token_hash,
    verify_password,
)
from .config import settings
from .database import get_session, session_scope
from .defaults import INITIAL_SANDBOX_CENTS
from .errors import ApiError
from .models import AuthSession, PaymentTransaction, TransactionAttempt, User
from .paypal_client import PayPalClient
from .schemas import (
    ApprovalListResponse,
    ApprovalRequest,
    AssistantRequest,
    AssistantResponse,
    AuthResponse,
    ChangePasswordRequest,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationMessagesResponse,
    ConversationSummaryResponse,
    ConversationUpdateRequest,
    LedgerItemResponse,
    LedgerPageResponse,
    LoginRequest,
    PaymentRequest,
    PaymentResponse,
    PolicyInput,
    PolicyResponse,
    PolicyVersionListResponse,
    PolicyVersionSummary,
    RegistrationRequest,
    RegistrationResponse,
    RejectionRequest,
    ResetRequest,
    ResetResponse,
    ReversalRequest,
    SpendSummaryResponse,
    TopUpRequest,
    TopUpResponse,
    TransactionDetailResponse,
    TransactionPageResponse,
    TransactionResponse,
    UserResponse,
    WalletBalanceResponse,
)
from .services.accounts import EmailAlreadyExists, create_account
from .services.assistant import (
    ConversationArchived,
    ConversationNotFound,
    create_conversation,
    list_conversations,
    list_messages,
    refresh_assistant_payment_state,
    run_assistant,
    update_conversation,
)
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
from .services.policies import (
    PolicyError,
    PolicyUnchanged,
    get_current_policy,
    list_policy_versions,
    reset_policy,
    save_policy,
    spend_summary as build_spend_summary,
)
from .services.paypal import ProviderUnavailable, submit_or_reconcile_payout
from .services.sandbox import ResetRateLimited, reset_sandbox
from .services.transactions import (
    AlreadyActioned,
    IntegrationUnavailable,
    NotReversible,
    PolicyBlocked,
    PolicyChanged,
    TransactionIdempotencyConflict,
    TransactionInProgress,
    TransactionNotFound,
    TransactionServiceError,
    approve_transaction as approve_payment,
    create_payment_request,
    get_owned_transaction,
    list_pending_approvals,
    list_transactions as query_transactions,
    reject_transaction as reject_payment,
    retry_transaction,
    reverse_transaction,
    transaction_detail,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with session_scope() as session:
        session.exec(text("SELECT 1 FROM users LIMIT 1")).all()
    app.state.paypal_client = PayPalClient()
    logger.info("Pactra sandbox API started")
    try:
        yield
    finally:
        await app.state.paypal_client.close()


app = FastAPI(
    title="Pactra API",
    description="AI agent payment governance for PayPal",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
    expose_headers=["X-CSRF-Token", "X-Request-ID"],
)


@app.middleware("http")
async def request_context_and_security_headers(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
    )
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    error = {
        "code": exc.code,
        "message": exc.message,
        "request_id": request.state.request_id,
    }
    if exc.details:
        error["details"] = exc.details
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error},
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


def _transaction_response(transaction: Any) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        type=transaction.type,
        vendor=transaction.vendor,
        recipient=transaction.recipient,
        amount_cents=transaction.amount_cents,
        currency=transaction.currency,
        category=transaction.category,
        reason=transaction.reason,
        status=transaction.status,
        sandbox_generation=transaction.sandbox_generation,
        policy_version=transaction.policy_version,
        rail=transaction.rail,
        rail_reference=transaction.rail_reference,
        provider_batch_id=transaction.provider_batch_id,
        provider_item_id=transaction.provider_item_id,
        provider_status=transaction.provider_status,
        failure_code=transaction.failure_code,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        completed_at=transaction.completed_at,
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
        f"register:{client_ip(request)}",
        limit=settings.auth_registration_rate_limit_per_hour,
        window=timedelta(hours=1),
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
def current_user(response: Response, context: AuthDependency) -> AuthResponse:
    set_csrf_response_header(response, context.raw_token)
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


@app.post("/api/wallet/reset", response_model=ResetResponse)
def reset_wallet_sandbox(
    payload: ResetRequest,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> ResetResponse:
    if payload.confirmation != "RESET":
        raise ApiError(400, "CONFIRMATION_REQUIRED", "Type RESET to confirm")
    try:
        result = reset_sandbox(
            db_session,
            user=context.user,
            idempotency_key=payload.idempotency_key,
        )
        db_session.commit()
    except ResetRateLimited as exc:
        db_session.rollback()
        raise ApiError(429, "RATE_LIMITED", str(exc)) from exc
    except TransactionInProgress as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    return ResetResponse(
        reset=True,
        balance_cents=result.balance_cents,
        sandbox_generation=result.sandbox_generation,
        history_preserved=True,
    )


@app.post("/api/chat", response_model=AssistantResponse)
async def chat(
    payload: AssistantRequest,
    request: Request,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> AssistantResponse:
    auth_rate_limiter.check(
        f"assistant:{context.user.id}:{client_ip(request)}",
        limit=20,
        window=timedelta(minutes=1),
    )
    try:
        result = await run_assistant(
            db_session,
            user=context.user,
            message=payload.message,
            conversation_id=payload.conversation_id,
            request_id=payload.request_id,
        )
    except ConversationNotFound as exc:
        raise ApiError(404, "NOT_FOUND", "Conversation not found") from exc
    except ConversationArchived as exc:
        raise ApiError(409, "CONVERSATION_ARCHIVED", str(exc)) from exc

    client = getattr(request.app.state, "paypal_client", None)
    for transaction_id in result.transaction_ids:
        transaction = get_owned_transaction(
            db_session,
            user_id=context.user.id,
            transaction_id=transaction_id,
        )
        if transaction.rail != "paypal_sandbox_payouts" or transaction.status != "executing":
            continue
        if client is None:
            continue
        try:
            await submit_or_reconcile_payout(
                db_session, client=client, transaction=transaction
            )
            db_session.commit()
        except ProviderUnavailable:
            db_session.commit()
    result = refresh_assistant_payment_state(
        db_session,
        user_id=context.user.id,
        request_id=payload.request_id,
        result=result,
    )
    db_session.commit()
    return AssistantResponse(
        conversation_id=result.conversation_id,
        reply=result.reply,
        tool_calls=result.tool_calls,
        transactions_created=result.transaction_ids,
    )


def _conversation_summary(summary) -> ConversationSummaryResponse:
    conversation = summary.conversation
    return ConversationSummaryResponse(
        id=conversation.id,
        title=conversation.title,
        message_count=summary.message_count,
        preview=summary.preview,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        archived_at=conversation.archived_at,
    )


@app.get("/api/conversations", response_model=ConversationListResponse)
def get_conversations(
    context: AuthDependency,
    db_session: SessionDependency,
    include_archived: bool = False,
) -> ConversationListResponse:
    items = list_conversations(
        db_session,
        user_id=context.user.id,
        include_archived=include_archived,
    )
    return ConversationListResponse(items=[_conversation_summary(item) for item in items])


@app.post(
    "/api/conversations",
    response_model=ConversationSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_conversation(
    payload: ConversationCreateRequest,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> ConversationSummaryResponse:
    conversation = create_conversation(
        db_session,
        user_id=context.user.id,
        title=payload.title,
    )
    db_session.commit()
    return ConversationSummaryResponse(
        id=conversation.id,
        title=conversation.title,
        message_count=0,
        preview=None,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        archived_at=conversation.archived_at,
    )


@app.patch(
    "/api/conversations/{conversation_id}",
    response_model=ConversationSummaryResponse,
)
def change_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> ConversationSummaryResponse:
    try:
        conversation = update_conversation(
            db_session,
            user_id=context.user.id,
            conversation_id=conversation_id,
            title=payload.title,
            archived=payload.archived,
        )
        db_session.commit()
    except ConversationNotFound as exc:
        db_session.rollback()
        raise ApiError(404, "NOT_FOUND", "Conversation not found") from exc
    messages = list_messages(
        db_session,
        user_id=context.user.id,
        conversation_id=conversation.id,
    )
    visible_messages = [message for message in messages if message.role != "tool"]
    preview = (
        " ".join(visible_messages[-1].content.split())[:140]
        if visible_messages
        else None
    )
    return ConversationSummaryResponse(
        id=conversation.id,
        title=conversation.title,
        message_count=len(messages),
        preview=preview,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        archived_at=conversation.archived_at,
    )


@app.get(
    "/api/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
def get_conversation_messages(
    conversation_id: str,
    context: AuthDependency,
    db_session: SessionDependency,
) -> ConversationMessagesResponse:
    try:
        messages = list_messages(
            db_session,
            user_id=context.user.id,
            conversation_id=conversation_id,
        )
    except ConversationNotFound as exc:
        raise ApiError(404, "NOT_FOUND", "Conversation not found") from exc
    return ConversationMessagesResponse(
        items=[
            ConversationMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                tool_calls=message.tool_calls,
                created_at=message.created_at,
            )
            for message in messages
        ]
    )


@app.get("/api/policy", response_model=PolicyResponse)
def get_policy(
    context: AuthDependency, db_session: SessionDependency
) -> PolicyResponse:
    try:
        policy = get_current_policy(db_session, context.user.id)
    except PolicyError as exc:
        raise ApiError(404, "NOT_FOUND", str(exc)) from exc
    return PolicyResponse(id=policy.id, version=policy.version, policy=policy.policy_json)


@app.get("/api/policies", response_model=PolicyVersionListResponse)
def get_policy_history(
    context: AuthDependency, db_session: SessionDependency
) -> PolicyVersionListResponse:
    items = list_policy_versions(db_session, user_id=context.user.id)
    return PolicyVersionListResponse(
        items=[
            PolicyVersionSummary(
                id=item.id,
                version=item.version,
                policy=item.policy_json,
                created_at=item.created_at,
            )
            for item in items
        ]
    )


@app.put("/api/policy", response_model=PolicyResponse)
def update_policy(
    payload: PolicyInput,
    request: Request,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> PolicyResponse:
    auth_rate_limiter.check(
        f"policy:{context.user.id}:{client_ip(request)}",
        limit=20,
        window=timedelta(hours=1),
    )
    try:
        policy_json = payload.validated_policy()
        policy = save_policy(
            db_session, user_id=context.user.id, policy_json=policy_json
        )
        db_session.commit()
    except ValueError as exc:
        db_session.rollback()
        raise ApiError(400, "POLICY_INVALID", str(exc)) from exc
    except PolicyUnchanged as exc:
        db_session.rollback()
        raise ApiError(409, "POLICY_UNCHANGED", str(exc)) from exc
    except PolicyError as exc:
        db_session.rollback()
        raise ApiError(400, "POLICY_INVALID", str(exc)) from exc
    return PolicyResponse(id=policy.id, version=policy.version, policy=policy.policy_json)


@app.post("/api/policy/reset", response_model=PolicyResponse)
def reset_account_policy(
    context: MutationAuthDependency, db_session: SessionDependency
) -> PolicyResponse:
    try:
        policy = reset_policy(db_session, user_id=context.user.id)
        db_session.commit()
    except PolicyError as exc:
        db_session.rollback()
        raise ApiError(400, "POLICY_INVALID", str(exc)) from exc
    return PolicyResponse(id=policy.id, version=policy.version, policy=policy.policy_json)


@app.post(
    "/api/transactions",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    payload: PaymentRequest,
    request: Request,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> PaymentResponse:
    auth_rate_limiter.check(
        f"payment:{context.user.id}:{client_ip(request)}",
        limit=30,
        window=timedelta(minutes=1),
    )
    if payload.type == "payout" and payload.recipient is None:
        raise ApiError(400, "VALIDATION_ERROR", "A recipient email is required for payouts")
    if payload.rail == "paypal_sandbox_payouts" and payload.type != "payout":
        raise ApiError(400, "VALIDATION_ERROR", "PayPal Sandbox is available only for payouts")
    request_payload = payload.model_dump(mode="python")
    request_payload["recipient"] = (
        str(request_payload["recipient"]) if request_payload["recipient"] else None
    )
    request_payload["source"] = "manual"
    try:
        result = create_payment_request(
            db_session, user=context.user, payload=request_payload
        )
        db_session.commit()
    except PolicyBlocked as exc:
        db_session.commit()
        transaction_body = _transaction_response(exc.transaction).model_dump(mode="json")
        policy_body = exc.decision.snapshot()
        code = exc.decision.reason_code or "POLICY_BLOCKED"
        status_code = 402 if code == "INSUFFICIENT_FUNDS" else 422
        public_code = "INSUFFICIENT_FUNDS" if status_code == 402 else "POLICY_BLOCKED"
        raise ApiError(
            status_code,
            public_code,
            "Your available sandbox balance is too low."
            if status_code == 402
            else "This request is blocked by your spending policy.",
            details={"transaction": transaction_body, "policy_result": policy_body},
        ) from exc
    except TransactionIdempotencyConflict as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    except IntegrationUnavailable as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    except LedgerError as exc:
        db_session.rollback()
        raise ApiError(409, "INSUFFICIENT_FUNDS", str(exc)) from exc
    if (
        result.transaction.rail == "paypal_sandbox_payouts"
        and result.transaction.status == "executing"
    ):
        client = getattr(request.app.state, "paypal_client", None)
        if client is None:
            raise ApiError(503, "PROVIDER_UNAVAILABLE", "PayPal client is unavailable")
        try:
            await submit_or_reconcile_payout(
                db_session, client=client, transaction=result.transaction
            )
            db_session.commit()
        except ProviderUnavailable:
            # Unknown outcomes stay executing with their reservation. Definite
            # pre-submission failures are persisted as failed by the service.
            db_session.commit()
        if result.transaction.status == "failed":
            raise ApiError(
                502,
                "PROVIDER_UNAVAILABLE",
                "PayPal Sandbox payout failed.",
                details={
                    "transaction": _transaction_response(
                        result.transaction
                    ).model_dump(mode="json")
                },
            )
        wallet = get_wallet_for_user(db_session, context.user.id)
        result = type(result)(
            transaction=result.transaction,
            policy_result=result.transaction.policy_result,
            balance=wallet_balance(db_session, wallet),
            replayed=False,
        )
    return PaymentResponse(
        transaction=_transaction_response(result.transaction),
        policy_result=result.policy_result,
        balance=_balance_response(result.balance),
    )


@app.get("/api/transactions", response_model=TransactionPageResponse)
def list_account_transactions(
    db_session: SessionDependency,
    context: AuthDependency,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            pattern="^(draft|pending_approval|executing|completed|blocked|rejected|failed|cancelled|reversed)$",
        ),
    ] = None,
    category: Annotated[str | None, Query(min_length=2, max_length=32)] = None,
    transaction_type: Annotated[
        str | None,
        Query(alias="type", pattern="^(vendor_payment|payout|sandbox_transfer)$"),
    ] = None,
    vendor: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    generation: Literal["current", "all"] = "current",
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> TransactionPageResponse:
    if from_date and to_date:
        if to_date < from_date:
            raise ApiError(400, "INVALID_DATE_RANGE", "End date must be on or after start date")
        if (to_date - from_date).days > 90:
            raise ApiError(400, "INVALID_DATE_RANGE", "Date range cannot exceed 90 days")
    created_from = (
        datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        if from_date
        else None
    )
    created_to = (
        datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        if to_date
        else None
    )
    wallet = get_wallet_for_user(db_session, context.user.id)
    try:
        items, next_cursor = query_transactions(
            db_session,
            user_id=context.user.id,
            generation=wallet.sandbox_generation if generation == "current" else None,
            status=status_filter,
            category=category,
            transaction_type=transaction_type,
            vendor=vendor,
            created_from=created_from,
            created_to=created_to,
            cursor=cursor,
            limit=limit,
        )
    except TransactionServiceError as exc:
        raise ApiError(400, "INVALID_CURSOR", str(exc)) from exc
    return TransactionPageResponse(
        items=[_transaction_response(item) for item in items],
        next_cursor=next_cursor,
    )


@app.get("/api/transactions/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction_detail(
    transaction_id: str,
    db_session: SessionDependency,
    context: AuthDependency,
) -> TransactionDetailResponse:
    try:
        detail = transaction_detail(
            db_session, user_id=context.user.id, transaction_id=transaction_id
        )
    except TransactionNotFound as exc:
        raise ApiError(404, "NOT_FOUND", "Transaction not found") from exc
    return TransactionDetailResponse(
        transaction=_transaction_response(detail["transaction"]),
        policy_checks=detail["policy_checks"],
        ledger_entries=detail["ledger_entries"],
        events=detail["events"],
        attempts=detail["attempts"],
    )


@app.post("/api/transactions/{transaction_id}/reverse")
def reverse_completed_transaction(
    transaction_id: str,
    payload: ReversalRequest,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> dict[str, Any]:
    try:
        transaction, journal = reverse_transaction(
            db_session,
            user=context.user,
            transaction_id=transaction_id,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason,
        )
        db_session.commit()
    except TransactionNotFound as exc:
        db_session.rollback()
        raise ApiError(404, "NOT_FOUND", "Transaction not found") from exc
    except NotReversible as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    except TransactionIdempotencyConflict as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    return {
        "transaction": _transaction_response(transaction).model_dump(mode="json"),
        "ledger_journal": {
            "id": journal.id,
            "journal_type": journal.journal_type,
            "created_at": journal.created_at,
        },
    }


@app.post("/api/transactions/{transaction_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_failed_transaction(
    transaction_id: str,
    payload: ApprovalRequest,
    request: Request,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> dict[str, Any]:
    try:
        transaction, attempt = retry_transaction(
            db_session,
            user=context.user,
            transaction_id=transaction_id,
            idempotency_key=payload.idempotency_key,
        )
        db_session.commit()
    except TransactionNotFound as exc:
        db_session.rollback()
        raise ApiError(404, "NOT_FOUND", "Transaction not found") from exc
    except AlreadyActioned as exc:
        db_session.rollback()
        raise ApiError(409, "NOT_RETRYABLE", str(exc)) from exc
    except IntegrationUnavailable as exc:
        db_session.rollback()
        raise ApiError(409, "PROVIDER_OUTCOME_UNKNOWN", str(exc)) from exc
    except LedgerError as exc:
        db_session.rollback()
        raise ApiError(409, "INSUFFICIENT_FUNDS", str(exc)) from exc
    if transaction.rail == "paypal_sandbox_payouts" and transaction.status == "executing":
        client = getattr(request.app.state, "paypal_client", None)
        if client is None:
            raise ApiError(503, "PROVIDER_UNAVAILABLE", "PayPal client is unavailable")
        try:
            await submit_or_reconcile_payout(
                db_session, client=client, transaction=transaction
            )
            db_session.commit()
        except ProviderUnavailable:
            db_session.commit()
    return {
        "transaction": _transaction_response(transaction).model_dump(mode="json"),
        "attempt": {
            "id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "status": attempt.status,
            "rail_request_id": attempt.rail_request_id,
        },
    }


@app.get("/api/approvals", response_model=ApprovalListResponse)
def get_approvals(
    context: AuthDependency, db_session: SessionDependency
) -> ApprovalListResponse:
    items = list_pending_approvals(db_session, user_id=context.user.id)
    return ApprovalListResponse(items=[_transaction_response(item) for item in items])


@app.post("/api/approvals/{transaction_id}/approve", response_model=TransactionResponse)
async def approve_pending_transaction(
    transaction_id: str,
    payload: ApprovalRequest,
    request: Request,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> TransactionResponse:
    try:
        transaction = approve_payment(
            db_session,
            user=context.user,
            transaction_id=transaction_id,
            idempotency_key=payload.idempotency_key,
        )
        db_session.commit()
    except PolicyChanged as exc:
        db_session.commit()
        raise ApiError(
            409,
            exc.code,
            str(exc),
            details={
                "transaction": _transaction_response(exc.transaction).model_dump(mode="json")
            },
        ) from exc
    except TransactionNotFound as exc:
        db_session.rollback()
        raise ApiError(404, "NOT_FOUND", "Transaction not found") from exc
    except (AlreadyActioned, TransactionIdempotencyConflict) as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    except IntegrationUnavailable as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    if transaction.rail == "paypal_sandbox_payouts" and transaction.status == "executing":
        client = getattr(request.app.state, "paypal_client", None)
        if client is None:
            raise ApiError(503, "PROVIDER_UNAVAILABLE", "PayPal client is unavailable")
        try:
            await submit_or_reconcile_payout(
                db_session, client=client, transaction=transaction
            )
            db_session.commit()
        except ProviderUnavailable:
            db_session.commit()
    return _transaction_response(transaction)


@app.get("/api/integrations/paypal/status")
def paypal_integration_status(
    context: AuthDependency, db_session: SessionDependency
) -> dict[str, Any]:
    configured = bool(
        settings.paypal_payouts_enabled
        and settings.paypal_client_id
        and settings.paypal_client_secret
        and not settings.paypal_mock_mode
        and settings.paypal_base_url.rstrip("/")
        == "https://api-m.sandbox.paypal.com"
    )
    latest_success = db_session.exec(
        select(TransactionAttempt.finished_at)
        .join(
            PaymentTransaction,
            PaymentTransaction.id == TransactionAttempt.transaction_id,
        )
        .where(
            PaymentTransaction.user_id == context.user.id,
            TransactionAttempt.rail == "paypal_sandbox_payouts",
            TransactionAttempt.status == "completed",
        )
        .order_by(TransactionAttempt.finished_at.desc())
        .limit(1)
    ).one_or_none()
    latest_error = db_session.exec(
        select(TransactionAttempt.response_code)
        .join(
            PaymentTransaction,
            PaymentTransaction.id == TransactionAttempt.transaction_id,
        )
        .where(
            PaymentTransaction.user_id == context.user.id,
            TransactionAttempt.rail == "paypal_sandbox_payouts",
            TransactionAttempt.response_code.is_not(None),
            TransactionAttempt.status.in_(["failed", "unknown"]),
        )
        .order_by(TransactionAttempt.started_at.desc())
        .limit(1)
    ).one_or_none()
    return {
        "configured": configured,
        "environment": "sandbox",
        "capabilities": ["payouts"],
        "test_recipient_email": settings.paypal_test_recipient_email or None,
        "last_success_at": latest_success,
        "last_error_code": latest_error,
    }


@app.post("/api/transactions/{transaction_id}/reconcile", response_model=TransactionResponse)
async def reconcile_paypal_transaction(
    transaction_id: str,
    request: Request,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> TransactionResponse:
    try:
        transaction = get_owned_transaction(
            db_session,
            user_id=context.user.id,
            transaction_id=transaction_id,
            for_update=True,
        )
    except TransactionNotFound as exc:
        raise ApiError(404, "NOT_FOUND", "Transaction not found") from exc
    if transaction.rail != "paypal_sandbox_payouts" or transaction.status not in {
        "executing",
        "completed",
    }:
        raise ApiError(409, "NOT_RECONCILABLE", "This transaction cannot be reconciled")
    client = getattr(request.app.state, "paypal_client", None)
    if client is None:
        raise ApiError(503, "PROVIDER_UNAVAILABLE", "PayPal client is unavailable")
    try:
        await submit_or_reconcile_payout(
            db_session, client=client, transaction=transaction
        )
        db_session.commit()
    except ProviderUnavailable as exc:
        db_session.commit()
        raise ApiError(502, "PROVIDER_UNAVAILABLE", str(exc)) from exc
    return _transaction_response(transaction)


@app.post("/api/approvals/{transaction_id}/reject", response_model=TransactionResponse)
def reject_pending_transaction(
    transaction_id: str,
    payload: RejectionRequest,
    context: MutationAuthDependency,
    db_session: SessionDependency,
) -> TransactionResponse:
    try:
        transaction = reject_payment(
            db_session,
            user=context.user,
            transaction_id=transaction_id,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason.strip() if payload.reason else None,
        )
        db_session.commit()
    except TransactionNotFound as exc:
        db_session.rollback()
        raise ApiError(404, "NOT_FOUND", "Transaction not found") from exc
    except (AlreadyActioned, TransactionIdempotencyConflict) as exc:
        db_session.rollback()
        raise ApiError(409, exc.code, str(exc)) from exc
    return _transaction_response(transaction)


@app.get("/api/spend-summary", response_model=SpendSummaryResponse)
def get_spend_summary(
    db_session: SessionDependency, context: AuthDependency
) -> SpendSummaryResponse:
    wallet = get_wallet_for_user(db_session, context.user.id)
    summary = build_spend_summary(
        db_session, user_id=context.user.id, wallet=wallet
    )
    return SpendSummaryResponse(**summary)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/ready")
def readiness(db_session: SessionDependency) -> dict[str, Any]:
    try:
        db_session.exec(text("SELECT 1")).one()
    except Exception as exc:
        logger.exception("Database readiness check failed")
        raise ApiError(503, "DATABASE_UNAVAILABLE", "Database is unavailable") from exc
    return {
        "status": "ready",
        "database": "ok",
        "sandbox_mode": True,
        "internal_sandbox_available": True,
        "ai_enabled": settings.ai_enabled,
        "ai_configured": bool(settings.ai_enabled and settings.gemini_api_key),
        "paypal_payouts_configured": bool(
            settings.paypal_payouts_enabled
            and settings.paypal_client_id
            and settings.paypal_client_secret
            and settings.paypal_test_recipient_email
            and not settings.paypal_mock_mode
            and settings.paypal_base_url.rstrip("/")
            == "https://api-m.sandbox.paypal.com"
        ),
    }
