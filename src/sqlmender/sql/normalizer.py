"""Normalize SQL with sqlglot so semantically-equal queries compare equal.

We parse to an AST and re-serialize in a canonical dialect/format (lowercase
identifiers off, normalized whitespace, normalized functions). This is used both
for de-duplicating generated data and for a lenient string-level equivalence check
(execution accuracy is the primary metric; this is the secondary one)."""

from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers


def normalize_sql(sql: str, dialect: str = "sqlite") -> str:
    """Return a canonical string form of a SQL query. Raises on unparseable SQL."""
    tree = sqlglot.parse_one(sql, read=dialect)
    tree = normalize_identifiers(tree)
    # Canonical: sorted no, but consistent quoting/spacing + lowercased keywords.
    return tree.sql(dialect=dialect, normalize=True, pretty=False)


def sql_equivalent(a: str, b: str, dialect: str = "sqlite") -> bool:
    """True if two SQL strings normalize to the same canonical form."""
    try:
        return normalize_sql(a, dialect) == normalize_sql(b, dialect)
    except Exception:  # noqa: BLE001
        # Fall back to a whitespace/case-insensitive compare if either won't parse.
        return " ".join(a.lower().split()) == " ".join(b.lower().split())


def is_parseable(sql: str, dialect: str = "sqlite") -> bool:
    try:
        sqlglot.parse_one(sql, read=dialect)
        return True
    except Exception:  # noqa: BLE001
        return False


def is_select_only(sql: str, dialect: str = "sqlite") -> bool:
    """True only if the statement is a single read-only SELECT (no DML/DDL)."""
    try:
        parsed = sqlglot.parse(sql, read=dialect)
    except Exception:  # noqa: BLE001
        return False
    if len(parsed) != 1 or parsed[0] is None:
        return False
    stmt = parsed[0]
    # Reject anything that is (or contains) a write/DDL command.
    forbidden = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Pragma,
    )
    if isinstance(stmt, forbidden):
        return False
    return stmt.find(*forbidden) is None and isinstance(stmt, (exp.Select, exp.Subquery, exp.Union))
