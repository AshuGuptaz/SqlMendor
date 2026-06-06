"""Shared prompt construction so training data and inference use the IDENTICAL
format (a mismatch here silently destroys accuracy)."""

from __future__ import annotations

from sqlmender.db.schema_info import SCHEMA_DESCRIPTION

INSTRUCTION = (
    "You are an expert data analyst. Given the database schema and a question, write a "
    "single SQLite SQL query that answers it. Return ONLY the SQL, no explanation."
)


def build_prompt(question: str) -> str:
    return (
        f"{INSTRUCTION}\n\n### Schema:\n{SCHEMA_DESCRIPTION}\n\n"
        f"### Question:\n{question}\n\n### SQL:\n"
    )
