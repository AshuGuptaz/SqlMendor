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


def write_split(
    examples: list[SQLExample], test_frac: float = 0.1, seed: int = 42
) -> tuple[int, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    rng.shuffle(examples)
    n_test = max(100, int(len(examples) * test_frac))
    test, train = examples[:n_test], examples[n_test:]
    for name, rows in (("train", train), ("test", test)):
        path = DATA_DIR / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for ex in rows:
                f.write(json.dumps(ex.model_dump(), ensure_ascii=False) + "\n")
        logger.success("wrote {} ({} rows)", path, len(rows))
    return len(train), len(test)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rebuild-db", action="store_true", help="Rebuild the SQLite DB first.")
    args = ap.parse_args()

    s = get_settings()
    if args.rebuild_db or not Path(s.db_path).exists():
        build(s.db_path)

    examples = build_dataset(args.seed)
    examples = validate_executes(examples, s.db_path)
    n_train, n_test = write_split(examples, seed=args.seed)
    logger.success("Done: {} train / {} test", n_train, n_test)


if __name__ == "__main__":
    main()
