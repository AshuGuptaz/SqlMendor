"""HeuristicGenerator: pattern coverage + the real column-repair behaviour."""

from __future__ import annotations

import pytest

from sqlmender.llm.generator import HeuristicGenerator, get_generator
from sqlmender.sql.normalizer import is_select_only

G = HeuristicGenerator()


@pytest.mark.parametrize(
    "q,frag",
    [
        ("What are the 5 most expensive products?", "ORDER BY price DESC LIMIT 5"),
        ("What are the 3 cheapest products?", "ORDER BY price ASC LIMIT 3"),
        ("How many delivered orders are there?", "status = 'delivered'"),
        ("How many customers are from Japan?", "country = 'Japan'"),
        ("Show customers in Paris", "city = 'Paris'"),
        ("Which products cost less than 50 dollars?", "price < 50"),
        ("Which products cost more than 200 dollars?", "price > 200"),
        ("What is the average product price?", "AVG(price)"),
        ("How many products are out of stock?", "stock = 0"),
        ("What is the total revenue from shipped orders?", "SUM(total)"),
        ("List the distinct order statuses", "DISTINCT status"),
        ("How many reviews gave a rating of 4?", "rating = 4"),
    ],
)
def test_patterns_produce_valid_select(q, frag):
    sql = G.generate(q)
    assert is_select_only(sql)
    assert frag in sql


def test_unknown_question_returns_safe_fallback_select():
    sql = G.generate("tell me something interesting")
    assert is_select_only(sql)


def test_repair_fixes_known_column_synonym():
    fixed = G.generate(
        "x", repair_hint=("SELECT SUM(total_price) FROM order_items", "no such column: total_price")
    )
    assert "unit_price" in fixed and "total_price" not in fixed


def test_repair_returns_match_when_no_synonym():
    # error without a known synonym -> falls back to pattern match (still valid SQL)
    out = G.generate(
        "how many delivered orders are there?",
        repair_hint=("SELECT x FROM y", "no such column: zzz"),
    )
    assert is_select_only(out)


def test_get_generator_is_heuristic_without_mlx():
    assert get_generator().name == "heuristic"
