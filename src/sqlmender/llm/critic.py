"""The critic — execution-grounded.

Unlike an LLM-only critic, the database is the oracle here: a query that fails to
parse, isn't a read-only SELECT, errors at execution, or (optionally, once) returns
zero rows is a concrete signal to repair. This is the heart of the unified design —
the same self-correction idea as a self-healing RAG, but grounded in real execution
rather than a model's opinion."""

from __future__ import annotations

from dataclasses import dataclass

from sqlmender.config import Settings, get_settings
from sqlmender.sql.executor import QueryResult
from sqlmender.sql.normalizer import is_select_only


@dataclass
class Verdict:
    ok: bool
    should_repair: bool
    reason: str
    hint: tuple[str, str] | None = None  # (sql, error) fed back into the next attempt


def critique(
    question: str,
    sql: str,
    result: QueryResult,
    attempt: int,
    settings: Settings | None = None,
) -> Verdict:
    s = settings or get_settings()

    if not is_select_only(sql):
        return Verdict(
            False,
            True,
            "not a read-only SELECT",
            (sql, "statement is not a single read-only SELECT"),
        )
    if result.error is not None:
        return Verdict(False, True, f"execution error: {result.error}", (sql, result.error))
    if result.row_count == 0 and s.repair_on_empty_result and attempt == 1:
        # Give exactly one informed retry on an empty result; afterwards accept it.
        return Verdict(
            False,
            True,
            "query returned 0 rows",
            (sql, "query executed but returned 0 rows; the filter may be wrong"),
        )
    return Verdict(True, False, "grounded: query executed and returned results")
