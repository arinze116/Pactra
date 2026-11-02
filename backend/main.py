"""FastAPI application exposing Pactra's agent and governance dashboard APIs."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .agent import AgentConfigurationError, PactraAgent
from .config import settings
from .database import create_db_and_tables, get_session
from .models import ChatRequest, ChatResponse, SpendSummary, Transaction
from .paypal_client import PayPalClient, PayPalError
from .policy_engine import PolicyConfigurationError, PolicyEngine


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

SessionDependency = Annotated[Session, Depends(get_session)]


def _policy_engine(request: Request) -> PolicyEngine:
    return request.app.state.policy_engine


def _paypal_client(request: Request) -> PayPalClient:
    return request.app.state.paypal_client


def _agent(request: Request) -> PactraAgent:
    return request.app.state.agent


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    db_session: SessionDependency,
) -> ChatResponse:
    try:
        return await _agent(request).run(
            payload.message.strip(),
            payload.history,
            _policy_engine(request),
            _paypal_client(request),
            db_session,
        )
    except AgentConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Agent request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The payment agent could not complete this request.",
        ) from exc


@app.get("/api/transactions", response_model=list[Transaction])
def list_transactions(
    db_session: SessionDependency,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(approved|blocked|pending_approval)$")
    ] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 50,
) -> list[Transaction]:
    statement = select(Transaction)
    if status_filter:
        statement = statement.where(Transaction.status == status_filter)
    if category:
        statement = statement.where(Transaction.category == category.casefold())
    statement = statement.order_by(Transaction.timestamp.desc()).limit(limit)
    return list(db_session.exec(statement).all())


@app.get("/api/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(
    transaction_id: str, db_session: SessionDependency
) -> Transaction:
    transaction = db_session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@app.get("/api/spend-summary", response_model=list[SpendSummary])
def spend_summary(
    request: Request, db_session: SessionDependency
) -> list[SpendSummary]:
    return _policy_engine(request).get_summary(db_session)


@app.get("/api/policy", response_model=dict[str, Any])
def get_policy(request: Request) -> dict[str, Any]:
    return dict(_policy_engine(request).policy)


@app.post(
    "/api/policy/approve/{transaction_id}",
    response_model=Transaction,
)
async def approve_transaction(
    transaction_id: str,
    request: Request,
    db_session: SessionDependency,
) -> Transaction:
    transaction = db_session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    try:
        return await _agent(request).approve_transaction(
            transaction,
            _policy_engine(request),
            _paypal_client(request),
            db_session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
