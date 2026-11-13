"""The headline test must contain only SQL templates that never appear in training."""

from __future__ import annotations

from sqlmender.train.data_gen import build_dataset, split_by_template, sql_template


def _parts(seed: int = 42):
    return split_by_template(build_dataset(seed), seed=seed)


def test_sql_template_masks_literals():
    assert sql_template("SELECT name FROM p WHERE price > 200;") == sql_template(
        "select  name from p where price > 35.5"
    )
    assert sql_template("SELECT 1 FROM t WHERE c = 'India'") == sql_template(
        "SELECT 1 FROM t WHERE c = 'Brazil'"
    )
    assert sql_template("SELECT a FROM t") != sql_template("SELECT b FROM t")


def test_no_template_overlap_between_train_and_unseen():
    p = _parts()
    train = {sql_template(e.sql) for e in p["train"]}
    unseen = {sql_template(e.sql) for e in p["test_unseen"]}
    assert unseen and not (train & unseen)


def test_no_exact_sql_leakage_into_unseen():
    p = _parts()
    train_sql = {e.sql for e in p["train"]}
    assert not any(e.sql in train_sql for e in p["test_unseen"])


def test_seen_test_uses_only_training_templates_and_is_disjoint_rows():
    p = _parts()
    train_t = {sql_template(e.sql) for e in p["train"]}
    assert all(sql_template(e.sql) in train_t for e in p["test_seen"])
    train_rows = {(e.question, e.sql) for e in p["train"]}
    assert not any((e.question, e.sql) in train_rows for e in p["test_seen"])


def test_every_unseen_category_keeps_a_training_template():
    p = _parts()
    train_cats = {e.category for e in p["train"]}
    # a category may exist only in unseen if it had a single template; that must not happen
    assert {e.category for e in p["test_unseen"]} <= train_cats


def test_split_is_deterministic_and_covers_everything():
    a, b = _parts(7), _parts(7)
    assert [e.question for e in a["test_unseen"]] == [e.question for e in b["test_unseen"]]
    total = len(a["train"]) + len(a["test_seen"]) + len(a["test_unseen"])
    assert total == len(build_dataset(7))
