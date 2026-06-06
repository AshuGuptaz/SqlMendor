"""Generate SQL from a question using base model + trained LoRA adapter.

Exposes ``SQLGenerator`` (used by the API) and a CLI. Requires Apple Silicon (MLX)
and a trained adapter. The generated SQL is post-processed (strip code fences / take
the first statement) before it is handed to the safe executor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from sqlmender.config import Settings, get_settings
from sqlmender.train.prompt import build_prompt


def _clean_sql(text: str) -> str:
    text = text.strip()
    # model sometimes echoes the prompt — take everything after the last marker
    if "### SQL:" in text:
        text = text.split("### SQL:")[-1].strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        text = text.replace("sql", "", 1).strip() if text.lower().startswith("sql") else text
    # first statement only
    if ";" in text:
        text = text.split(";")[0] + ";"
    return text.strip()


class SQLGenerator:
    """Lazily loads the MLX model + adapter; callable question -> SQL string."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = None
        self._tok = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from mlx_lm import load  # requires Apple Silicon

        adapter = self.settings.adapter_path if Path(self.settings.adapter_path).exists() else None
        self._model, self._tok = load(self.settings.base_model, adapter_path=adapter)

    def generate(self, question: str, max_tokens: int = 256) -> str:
        self._ensure_loaded()
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        prompt = build_prompt(question)
        out = generate(
            self._model,
            self._tok,
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=make_sampler(temp=0.0),
            verbose=False,
        )
        return _clean_sql(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("question")
    ap.add_argument("--execute", action="store_true", help="Also run the SQL against the DB.")
    args = ap.parse_args()
    try:
        import mlx_lm  # noqa: F401
    except Exception as e:  # noqa: BLE001
        logger.error("MLX unavailable: {}. Needs an Apple Silicon Mac.", e)
        sys.exit(1)

    sql = SQLGenerator().generate(args.question)
    print("SQL:", sql)
    if args.execute:
        from sqlmender.sql.executor import execute_query

        res = execute_query(sql)
        print("error:" if res.error else f"rows ({res.row_count}):", res.error or res.rows[:10])


if __name__ == "__main__":
    main()
