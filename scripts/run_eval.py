"""Evaluate the agent on a held-out test set.

Execution accuracy = the agent's final SQL returns the same result set as the gold SQL.
Reported overall and per query category, plus how many answers were grounded on the first
try, repaired, or abstained.

The headline test is ``data/test_unseen.jsonl``: query *templates* never seen in training.
``data/test_seen.jsonl`` (new paraphrases of training templates) is reported alongside it so
the gap between memorised and unseen queries is visible. No numbers are fabricated: run this
to produce them.

    python scripts/run_eval.py --generator mlx --test data/test_unseen.jsonl --name unseen
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from loguru import logger

from sqlmender.agent.graph import build_default_agent
from sqlmender.agent.state import initial_state
from sqlmender.config import get_settings
from sqlmender.eval.metrics import execution_accuracy, results_match
from sqlmender.llm.generator import GroqGenerator, HeuristicGenerator, MLXGenerator
from sqlmender.sql.executor import execute_query

ROOT = Path(__file__).resolve().parents[1]


def pick_generator(name: str, settings):
    """auto = whatever the app would use (MLX, then Groq, then heuristic)."""
    if name == "auto":
        return None
    return {"heuristic": HeuristicGenerator, "mlx": MLXGenerator, "groq": GroqGenerator}[name](
        *([] if name == "heuristic" else [settings])
    )


def main() -> None:
    s = get_settings()
    data_dir = Path(s.db_path).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", default=str(data_dir / "test_unseen.jsonl"))
    ap.add_argument("--name", default="unseen", help="label used in the output file name")
    ap.add_argument("--generator", choices=["auto", "heuristic", "mlx", "groq"], default="auto")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default="", help="default: outputs/eval_<generator>_<name>.json")
    args = ap.parse_args()

    rows = [json.loads(x) for x in Path(args.test).read_text().splitlines() if x.strip()]
    if args.limit:
        rows = rows[: args.limit]
    gen = pick_generator(args.generator, s)
    agent = build_default_agent(s, generator=gen)
    gen_name = getattr(gen, "name", args.generator) if gen else "auto"

    pairs, first_try, repaired, abstained = [], 0, 0, 0
    per_cat: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        final = agent.invoke(initial_state(r["question"], s.max_repair_attempts))
        pred = final.get("sql", "SELECT 1")
        if final.get("status") == "abstained":
            abstained += 1
        elif final.get("attempts", 1) == 1:
            first_try += 1
        else:
            repaired += 1
        pairs.append({"pred_sql": pred, "gold_sql": r["sql"]})
        ok = results_match(execute_query(pred, s.db_path), execute_query(r["sql"], s.db_path))
        per_cat[r.get("category", "?")].append(ok)

    acc = execution_accuracy(pairs, s.db_path)
    n = len(rows)
    summary = {
        "generator": gen_name,
        "test_file": Path(args.test).name,
        "n": n,
        "execution_accuracy": round(acc["execution_accuracy"], 4),
        "pred_execution_rate": round(acc["pred_execution_rate"], 4),
        "grounded_first_try": first_try,
        "repaired": repaired,
        "abstained": abstained,
        "by_category": {
            c: {"n": len(v), "execution_accuracy": round(sum(v) / len(v), 3)}
            for c, v in sorted(per_cat.items())
        },
    }
    out = Path(args.out) if args.out else ROOT / "outputs" / f"eval_{gen_name}_{args.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    logger.success("eval -> {}", out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
