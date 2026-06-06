"""Agent state — a JSON-serialisable dict carried through the graph."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    attempts: int
    max_attempts: int
    few_shots: list[dict[str, Any]]
    sql: str
    result: dict[str, Any]  # {columns, rows, row_count, error}
    repair_hint: tuple[str, str] | None
    history: list[dict[str, Any]]  # [{attempt, sql, error, verdict}]
    status: str  # "running" | "ok" | "abstained"
    answer: str


def initial_state(question: str, max_attempts: int) -> AgentState:
    return AgentState(
        question=question,
        attempts=0,
        max_attempts=max_attempts,
        few_shots=[],
        repair_hint=None,
        history=[],
        status="running",
    )
