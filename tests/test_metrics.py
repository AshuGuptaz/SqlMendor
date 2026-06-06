from __future__ import annotations

from sqlmender.eval.metrics import execution_accuracy, results_match
from sqlmender.sql.executor import QueryResult


def test_results_match_order_insensitive():
    a = QueryResult(columns=["x"], rows=[[1], [2], [3]])
    b = QueryResult(columns=["x"], rows=[[3], [1], [2]])
    assert results_match(a, b, ordered=False)
    assert not results_match(a, b, ordered=True)


def test_execution_accuracy(db_path):
    perfect = [
        {"pred_sql": "SELECT COUNT(*) FROM products", "gold_sql": "SELECT COUNT(*) FROM products"}
    ]
    assert execution_accuracy(perfect, db_path)["execution_accuracy"] == 1.0
    mixed = perfect + [
        {"pred_sql": "SELECT COUNT(*) FROM customers", "gold_sql": "SELECT COUNT(*) FROM products"}
    ]
    assert execution_accuracy(mixed, db_path)["execution_accuracy"] == 0.5


def test_unsafe_pred_scores_zero(db_path):
    pairs = [{"pred_sql": "DROP TABLE products", "gold_sql": "SELECT COUNT(*) FROM products"}]
    assert execution_accuracy(pairs, db_path)["execution_accuracy"] == 0.0
