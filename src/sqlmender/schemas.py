"""Pydantic schemas for data + API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SQLExample(BaseModel):
    """A single (question, SQL) training/eval pair."""

    question: str = Field(min_length=1)
    sql: str = Field(min_length=1)
    category: str = "template"


class SQLRequest(BaseModel):
    question: str = Field(min_length=1)


class SQLResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[list]
    row_count: int
    error: str | None = None


class RepairStep(BaseModel):
    attempt: int
    sql: str
    error: str | None = None
    verdict: str
    ok: bool


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    question: str
    status: str  # "ok" | "abstained"
    answer: str
    sql: str | None = None
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    attempts: int = 0
    history: list[RepairStep] = []


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
