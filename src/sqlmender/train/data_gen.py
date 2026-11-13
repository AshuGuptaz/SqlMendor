"""Expand templates into a deduplicated, execution-validated dataset and split it
into train/test JSONL.

Augmentation: each base question is paraphrased into several grammatical surface
forms that map to the SAME SQL (this is standard text-to-SQL augmentation and is
what teaches phrasing-robustness). Every (question, SQL) pair is then checked to
PARSE and EXECUTE against the real SQLite DB before being kept — so the dataset
contains no broken queries.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from loguru import logger

from sqlmender.config import get_settings
from sqlmender.db.build_db import build
from sqlmender.schemas import SQLExample
from sqlmender.sql.executor import execute_query
from sqlmender.sql.normalizer import normalize_sql
from sqlmender.train.templates import generate_all, generate_cross_product

DATA_DIR = Path(get_settings().db_path).resolve().parent

# Lead-verb rewrites that stay grammatical for these question shapes.
_LEAD_REWRITES = {
    "List ": ["Show me ", "Give me ", "Return "],
    "Show ": ["List ", "Display "],
    "Which ": ["What "],
    "What are ": ["List "],
    "How many ": ["Count how many "],
}


def paraphrase(question: str) -> list[str]:
    """Return the original plus several same-meaning paraphrases."""
    variants = {question}
    for lead, repls in _LEAD_REWRITES.items():
        if question.startswith(lead):
            for r in repls:
                variants.add(r + question[len(lead) :])
    # "Can you ..." form (lowercase first letter of the original).
    variants.add("Can you " + question[0].lower() + question[1:])
    # Polite prefix.
    variants.add("Please " + question[0].lower() + question[1:])
    # Vocabulary swap.
    if "dollars" in question:
        variants.add(question.replace("dollars", "USD"))
    return list(variants)


def build_dataset(seed: int = 42) -> list[SQLExample]:
    bases = list(generate_all()) + list(generate_cross_product())
    logger.info("{} base template pairs", len(bases))

    seen_norm_q: set[tuple[str, str]] = set()
    examples: list[SQLExample] = []
    for base in bases:
        try:
            norm = normalize_sql(base.sql)
        except Exception:  # noqa: BLE001
            logger.warning("unparseable base SQL skipped: {}", base.sql)
            continue
        for q in paraphrase(base.question):
            key = (q.lower(), norm)
            if key in seen_norm_q:
                continue
            seen_norm_q.add(key)
            examples.append(SQLExample(question=q, sql=base.sql, category=base.category))
    logger.info("{} pairs after paraphrase + dedup", len(examples))
    random.Random(seed).shuffle(examples)
    return examples


def validate_executes(examples: list[SQLExample], db_path: str) -> list[SQLExample]:
    """Keep only pairs whose SQL executes without error against the DB."""
    kept = []
    for ex in examples:
        res = execute_query(ex.sql, db_path)
        if res.error is None:
            kept.append(ex)
        else:
            logger.warning("dropping non-executing SQL ({}): {}", res.error, ex.sql)
    logger.info("{} pairs execute cleanly against the DB", len(kept))
    return kept


_LITERAL = re.compile(r"'[^']*'|\b\d+(?:\.\d+)?\b")


def sql_template(sql: str) -> str:
    """Skeleton of a query with literals masked, e.g. ``... LIMIT 5`` and ``... LIMIT 3`` share
    one template. Used to split by *query shape*, not by wording."""
    s = re.sub(r"\s+", " ", sql.strip().rstrip(";")).lower()
    return _LITERAL.sub("?", s)


def split_by_template(
    examples: list[SQLExample],
    unseen_frac: float = 0.2,
    seen_frac: float = 0.1,
    seed: int = 42,
) -> dict:
    """Split so that the headline test set contains ONLY query templates never seen in training.

    A random split of paraphrased examples leaks: every test SQL also appears in train, so the
    model is graded on queries it memorised. Here whole templates are held out instead.

    Returns ``train``, ``test_seen`` (held-out paraphrases of *training* templates, used as the
    validation set), ``test_unseen`` (held-out templates, the honest test) and a ``report``.
    Every category keeps at least one training template.
    """
    rng = random.Random(seed)
    groups: dict[str, list[SQLExample]] = defaultdict(list)
    for ex in examples:
        groups[sql_template(ex.sql)].append(ex)

    by_cat: dict[str, list[str]] = defaultdict(list)
    for tpl in sorted(groups):
        by_cat[groups[tpl][0].category].append(tpl)
    for tpls in by_cat.values():
        rng.shuffle(tpls)

    target = unseen_frac * len(examples)
    held: set[str] = set()
    held_n = 0
    # Round-robin over categories so the unseen set is spread across query types.
    cats = sorted(by_cat)
    progress = True
    while held_n < target and progress:
        progress = False
        for cat in cats:
            candidates = [t for t in by_cat[cat] if t not in held]
            remaining_train = len(by_cat[cat]) - sum(1 for t in by_cat[cat] if t in held)
            if not candidates or remaining_train <= 1:
                continue
            tpl = candidates[0]
            if held_n and held_n + len(groups[tpl]) > 1.5 * target:
                continue
            held.add(tpl)
            held_n += len(groups[tpl])
            progress = True
            if held_n >= target:
                break

    unseen = [ex for t in sorted(held) for ex in groups[t]]
    pool = [ex for t in sorted(groups) if t not in held for ex in groups[t]]
    rng.shuffle(pool)
    n_seen = max(20, int(len(pool) * seen_frac))
    test_seen, train = pool[:n_seen], pool[n_seen:]

    train_templates = {sql_template(e.sql) for e in train}
    assert not (train_templates & held), "template leakage between train and unseen test"
    report = {
        "seed": seed,
        "train": len(train),
        "test_seen": len(test_seen),
        "test_unseen": len(unseen),
        "train_templates": len(train_templates),
        "unseen_templates": len(held),
        "unseen_template_sql": sorted(held),
        "unseen_by_category": dict(sorted(_count(e.category for e in unseen).items())),
        "train_by_category": dict(sorted(_count(e.category for e in train).items())),
    }
    return {"train": train, "test_seen": test_seen, "test_unseen": unseen, "report": report}


def _count(items) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for i in items:
        out[i] += 1
    return out


def _write(path: Path, rows: list[SQLExample]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ex in rows:
            f.write(json.dumps(ex.model_dump(), ensure_ascii=False) + "\n")
    logger.success("wrote {} ({} rows)", path, len(rows))


def write_split(
    examples: list[SQLExample],
    test_frac: float = 0.1,
    seed: int = 42,
    mode: str = "template",
) -> tuple[int, int]:
    """Write train/test JSONL. ``template`` (default) holds out whole query templates; ``random``
    reproduces the original leaky split, kept only so old results can be reproduced."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if mode == "random":
        rng = random.Random(seed)
        rng.shuffle(examples)
        n_test = max(100, int(len(examples) * test_frac))
        test, train = examples[:n_test], examples[n_test:]
        _write(DATA_DIR / "train.jsonl", train)
        _write(DATA_DIR / "test.jsonl", test)
        return len(train), len(test)

    parts = split_by_template(examples, seed=seed)
    _write(DATA_DIR / "train.jsonl", parts["train"])
    _write(DATA_DIR / "test_seen.jsonl", parts["test_seen"])
    _write(DATA_DIR / "test_unseen.jsonl", parts["test_unseen"])
    _write(DATA_DIR / "test.jsonl", parts["test_unseen"])  # headline test = unseen templates
    (DATA_DIR / "split_report.json").write_text(json.dumps(parts["report"], indent=2))
    logger.info(
        "template split: {}", {k: v for k, v in parts["report"].items() if isinstance(v, int)}
    )
    return len(parts["train"]), len(parts["test_unseen"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rebuild-db", action="store_true", help="Rebuild the SQLite DB first.")
    ap.add_argument(
        "--split",
        choices=["template", "random"],
        default="template",
        help="template = hold out whole SQL templates (honest); random = legacy leaky split",
    )
    args = ap.parse_args()

    s = get_settings()
    if args.rebuild_db or not Path(s.db_path).exists():
        build(s.db_path)

    examples = build_dataset(args.seed)
    examples = validate_executes(examples, s.db_path)
    n_train, n_test = write_split(examples, seed=args.seed, mode=args.split)
    logger.success("Done: {} train / {} test", n_train, n_test)


if __name__ == "__main__":
    main()
