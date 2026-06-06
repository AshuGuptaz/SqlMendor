from __future__ import annotations

import pytest

from sqlmender.sql.executor import UnsafeQueryError, execute_query


@pytest.mark.parametrize(
    "bad",
    [
        "INSERT INTO products VALUES (999,'x',1,2.0,3)",
        "UPDATE products SET price=0",
        "DELETE FROM products",
        "DROP TABLE products",
        "ALTER TABLE products ADD COLUMN h TEXT",
        "CREATE TABLE evil (id INTEGER)",
    ],
)
def test_mutations_rejected(db_path, bad):
    with pytest.raises(UnsafeQueryError):
        execute_query(bad, db_path)


def test_select_runs(db_path):
    res = execute_query("SELECT COUNT(*) FROM products", db_path)
    assert res.error is None and res.rows[0][0] >= 200


def test_row_cap(db_path):
    assert execute_query("SELECT * FROM order_items", db_path, max_rows=5).row_count == 5


def test_db_unchanged_after_rejected_mutation(db_path):
    before = execute_query("SELECT COUNT(*) FROM products", db_path).rows[0][0]
    with pytest.raises(UnsafeQueryError):
        execute_query("DELETE FROM products", db_path)
    assert execute_query("SELECT COUNT(*) FROM products", db_path).rows[0][0] == before
