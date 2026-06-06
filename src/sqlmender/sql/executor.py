"""Safe, read-only SQL execution against the SQLite eval DB.

Defenses:
  * AST-level check (sqlglot) that the statement is SELECT-only — rejects
    INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PRAGMA before anything touches the DB.
  * Connection opened read-only (file: URI, mode=ro) so writes fail at the engine
    level even if the parser is somehow bypassed.
  * A statement-progress timeout so a runaway query can't hang the process.
  * A row cap to bound memory.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from sqlmender.config import get_settings
from sqlmender.sql.normalizer import is_select_only


class UnsafeQueryError(ValueError):
    """Raised when a query is not a read-only SELECT."""


@dataclass
class QueryResult:
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    error: str | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _readonly_connection(db_path: str) -> sqlite3.Connection:
    uri = f"file:{Path(db_path).resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def execute_query(
    sql: str,
    db_path: str | None = None,
    timeout_seconds: float | None = None,
    max_rows: int | None = None,
) -> QueryResult:
    """Execute a read-only SELECT and return rows, or a QueryResult with .error set."""
    s = get_settings()
    db_path = db_path or s.db_path
    timeout_seconds = timeout_seconds if timeout_seconds is not None else s.query_timeout_seconds
    max_rows = max_rows if max_rows is not None else s.max_rows

    if not is_select_only(sql):
        raise UnsafeQueryError("Only read-only SELECT statements are permitted.")

    conn = _readonly_connection(db_path)
    # Hard timeout: abort if the query runs longer than the budget.
    deadline = time.perf_counter() + timeout_seconds

    def _progress_handler() -> int:
        return 1 if time.perf_counter() > deadline else 0

    conn.set_progress_handler(_progress_handler, 1000)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchmany(max_rows)]
        return QueryResult(columns=columns, rows=rows)
    except sqlite3.OperationalError as e:
        msg = "query timed out" if "interrupted" in str(e).lower() else str(e)
        return QueryResult(error=msg)
    except sqlite3.Error as e:
        return QueryResult(error=str(e))
    finally:
        conn.close()
