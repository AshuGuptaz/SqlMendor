"""Build the SQLite database from schema.sql + deterministic seed data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from loguru import logger

from sqlmender.config import get_settings
from sqlmender.db.seed import generate

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_INSERTS = {
    "categories": "INSERT INTO categories VALUES (?,?,?)",
    "customers": "INSERT INTO customers VALUES (?,?,?,?,?,?,?)",
    "products": "INSERT INTO products VALUES (?,?,?,?,?)",
    "orders": "INSERT INTO orders VALUES (?,?,?,?,?)",
    "order_items": "INSERT INTO order_items VALUES (?,?,?,?,?)",
    "reviews": "INSERT INTO reviews VALUES (?,?,?,?,?,?)",
}


def build(db_path: str | None = None, seed: int = 42) -> str:
    db_path = db_path or get_settings().db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(db_path).exists():
        Path(db_path).unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        data = generate(seed)
        for table, rows in data.items():
            conn.executemany(_INSERTS[table], rows)
            logger.info("inserted {} rows into {}", len(rows), table)
        conn.commit()
    finally:
        conn.close()
    logger.success("Built database -> {}", db_path)
    return db_path


if __name__ == "__main__":
    build()
