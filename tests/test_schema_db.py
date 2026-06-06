from __future__ import annotations

import sqlite3


def test_tables_populated(db_path):
    conn = sqlite3.connect(db_path)
    try:
        c = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ["categories", "customers", "products", "orders", "order_items", "reviews"]
        }
    finally:
        conn.close()
    assert c["customers"] >= 200 and c["products"] >= 200 and c["orders"] >= 200
    assert c["order_items"] >= c["orders"] and c["categories"] == 8


def test_no_orphans(db_path):
    conn = sqlite3.connect(db_path)
    try:
        op = conn.execute(
            "SELECT COUNT(*) FROM products p LEFT JOIN categories c "
            "ON p.category_id=c.category_id WHERE c.category_id IS NULL"
        ).fetchone()[0]
        oi = conn.execute(
            "SELECT COUNT(*) FROM order_items oi LEFT JOIN orders o "
            "ON oi.order_id=o.order_id WHERE o.order_id IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    assert op == 0 and oi == 0
