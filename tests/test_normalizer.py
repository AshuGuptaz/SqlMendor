from __future__ import annotations

from sqlmender.sql.normalizer import is_parseable, is_select_only, normalize_sql, sql_equivalent


def test_equivalent_normalize_equal():
    assert sql_equivalent(
        "SELECT name FROM products WHERE price < 100", "select  name from products where price<100"
    )


def test_non_equivalent_differ():
    assert not sql_equivalent(
        "SELECT name FROM products WHERE price < 100", "SELECT name FROM products WHERE price < 200"
    )


def test_parseable_and_select_only():
    assert is_parseable("SELECT 1")
    assert not is_parseable("SELECT * FROM t WHERE")
    assert is_select_only("SELECT * FROM products")
    assert not is_select_only("DROP TABLE products")
    assert normalize_sql("SELECT 1") == normalize_sql("select 1")
