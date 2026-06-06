"""API routes for SQLMender.

GET  /health           liveness
GET  /schema           the DB schema description (JWT)
POST /ask              run the self-healing agent on a question (JWT)
POST /sql              execute a provided read-only SELECT directly (JWT)
POST /auth/token       demo login -> bearer token
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from sqlmender.api.auth import authenticate, create_access_token, verify_token
from sqlmender.db.schema_info import SCHEMA_DESCRIPTION
from sqlmender.schemas import (
    AskRequest,
    AskResponse,
    RepairStep,
    SQLRequest,
    SQLResponse,
    TokenResponse,
)
from sqlmender.sql.executor import UnsafeQueryError, execute_query

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/schema")
def schema(_: str = Depends(verify_token)) -> dict[str, str]:
    return {"schema": SCHEMA_DESCRIPTION}


@router.post("/auth/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    if not authenticate(form_data.username, form_data.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return TokenResponse(access_token=create_access_token(form_data.username))


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request, _: str = Depends(verify_token)) -> AskResponse:
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    from sqlmender.agent.state import initial_state
    from sqlmender.config import get_settings

    s = get_settings()
    final = agent.invoke(initial_state(body.question, s.max_repair_attempts))
    res = final.get("result", {}) or {}
    return AskResponse(
        question=body.question,
        status=final.get("status", "ok"),
        answer=final.get("answer", ""),
        sql=final.get("sql"),
        columns=res.get("columns", []),
        rows=res.get("rows", []),
        row_count=res.get("row_count", 0),
        attempts=final.get("attempts", 0),
        history=[RepairStep(**h) for h in final.get("history", [])],
    )


@router.post("/sql", response_model=SQLResponse)
def run_sql(body: SQLRequest, _: str = Depends(verify_token)) -> SQLResponse:
    """Execute a provided read-only SELECT directly (no model) — the safe executor."""
    try:
        result = execute_query(body.question)  # 'question' carries the SQL here
    except UnsafeQueryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return SQLResponse(
        question=body.question,
        sql=body.question,
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        error=result.error,
    )
