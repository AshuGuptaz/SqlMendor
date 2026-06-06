from __future__ import annotations

from sqlmender.retrieval.example_index import ExampleIndex
from sqlmender.retrieval.schema_index import focused_schema, relevant_tables
from sqlmender.schemas import SQLExample


def test_example_index_retrieves_similar():
    ex = [
        SQLExample(
            question="How many delivered orders are there?",
            sql="SELECT COUNT(*) FROM orders WHERE status='delivered'",
        ),
        SQLExample(
            question="List the 5 most expensive products",
            sql="SELECT name FROM products ORDER BY price DESC LIMIT 5",
        ),
        SQLExample(question="Average product price", sql="SELECT AVG(price) FROM products"),
    ]
    idx = ExampleIndex(ex)
    top = idx.retrieve("how many orders were delivered?", k=1)
    assert len(top) == 1 and "orders" in top[0].sql


def test_example_index_empty_is_safe():
    assert ExampleIndex([]).retrieve("anything", k=3) == []


def test_schema_retrieval_selects_relevant_tables():
    t = relevant_tables("How many reviews gave a rating of 5?")
    assert "reviews" in t
    # FK expansion pulls in neighbours so joins remain possible
    assert "products" in t or "customers" in t


def test_focused_schema_is_subset_string():
    s = focused_schema("Which products cost less than 50 dollars?")
    assert "products(" in s and s.startswith("Tables:")
