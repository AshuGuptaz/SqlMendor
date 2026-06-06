from __future__ import annotations

from sqlmender.sql.normalizer import is_select_only
from sqlmender.train.data_gen import build_dataset, paraphrase, validate_executes
from sqlmender.train.templates import generate_all, generate_cross_product


def test_paraphrase_variants():
    v = paraphrase("List all products in the Electronics category.")
    assert len(v) >= 3 and len(set(v)) == len(v)


def test_template_sql_is_select_only():
    for ex in list(generate_all()) + list(generate_cross_product()):
        assert is_select_only(ex.sql), ex.sql


def test_build_dataset_substantial_and_unique():
    ds = build_dataset(seed=1)
    assert len(ds) > 500
    assert len({(e.question.lower(), e.sql) for e in ds}) == len(ds)


def test_validate_executes_filters(db_path):
    from sqlmender.schemas import SQLExample

    good = SQLExample(question="q", sql="SELECT 1", category="t")
    bad = SQLExample(question="q2", sql="SELECT * FROM nope", category="t")
    kept = validate_executes([good, bad], db_path)
    assert good in kept and bad not in kept
