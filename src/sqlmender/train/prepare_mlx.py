"""Convert train/test JSONL (question, sql) into the prompt/completion JSONL that
mlx-lm expects. Runs anywhere (no MLX needed)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loguru import logger

from sqlmender.config import get_settings
from sqlmender.train.prompt import build_prompt

DATA_DIR = Path(get_settings().db_path).resolve().parent
MLX_DIR = DATA_DIR / "mlx"


def convert(src: Path, dst: Path) -> int:
    rows = [json.loads(line) for line in src.read_text().splitlines() if line.strip()]
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        for r in rows:
            rec = {"prompt": build_prompt(r["question"]), "completion": " " + r["sql"].strip()}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.success("wrote {} ({} rows)", dst, len(rows))
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    args = ap.parse_args()
    d = Path(args.data_dir)
    convert(d / "train.jsonl", MLX_DIR / "train.jsonl")
    # mlx-lm expects a valid.jsonl; use the test split as validation.
    convert(d / "test.jsonl", MLX_DIR / "valid.jsonl")


if __name__ == "__main__":
    main()
