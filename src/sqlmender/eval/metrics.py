"""Execution accuracy — the headline metric.

A predicted SQL query is "correct" if it EXECUTES and returns the SAME result set
as the gold query. We compare result sets as multisets of rows (order-insensitive
by default, since SQL without ORDER BY has no guaranteed order), which is the
standard execution-accuracy definition used by Spider/WikiSQL-style evals."""

from __future__ import annotations

from collections import Counter

from sqlmender.sql.executor import QueryResult, execute_query


def _canonical_rows(result: QueryResult, ordered: bool):
    rows = [tuple(("" if v is None else v) for v in row) for row in result.rows]
    return rows if ordered else Counter(rows)


def results_match(pred: QueryResult, gold: QueryResult, ordered: bool = False) -> bool:
    if pred.error is not None or gold.error is not None:
        return False
    return _canonical_rows(pred, ordered) == _canonical_rows(gold, ordered)


def execution_accuracy(
    pairs: list[dict], db_path: str | None = None, ordered: bool = False
) -> dict[str, float]:
    """pairs: list of {"pred_sql": str, "gold_sql": str}.

    Returns execution_accuracy, pred_execution_rate (fraction that ran at all),
    and counts.
    """
    if not pairs:
        return {"execution_accuracy": 0.0, "pred_execution_rate": 0.0, "n": 0.0, "correct": 0.0}

    correct = 0
    ran = 0
    for p in pairs:
        pred = (
            execute_query(p["pred_sql"], db_path)
            if _safe(p["pred_sql"])
            else QueryResult(error="unsafe")
        )
        gold = (
            execute_query(p["gold_sql"], db_path)
            if _safe(p["gold_sql"])
            else QueryResult(error="unsafe")
        )
        if pred.error is None:
            ran += 1
        if results_match(pred, gold, ordered):
            correct += 1
    n = len(pairs)
    return {
        "execution_accuracy": correct / n,
        "pred_execution_rate": ran / n,
        "n": float(n),
        "correct": float(correct),
    }


def _safe(sql: str) -> bool:
    from sqlmender.sql.normalizer import is_select_only

    return is_select_only(sql)
