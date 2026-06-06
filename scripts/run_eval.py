"""Evaluate the agent on the held-out test set.

Computes execution accuracy (agent's final SQL vs. gold SQL, compared by result
set) plus operational stats: how many answers were grounded on the first try, how
many needed a repair, and how many abstained. With the heuristic generator this
gives a real baseline; swap in the fine-tuned MLX model on Apple Silicon to measure
the lift. No numbers are fabricated — run this to populate the README table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loguru import logger

from sqlmender.agent.graph import build_default_agent
from sqlmender.agent.state import initial_state
from sqlmender.config import get_settings
from sqlmender.eval.metrics import execution_accuracy

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", default=str(Path(s.db_path).resolve().parent / "test.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "eval.json"))
    args = ap.parse_args()

    rows = [json.loads(x) for x in Path(args.test).read_text().splitlines() if x.strip()]
    if args.limit:
        rows = rows[: args.limit]
    agent = build_default_agent(s)

    pairs, first_try, repaired, abstained = [], 0, 0, 0
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

    acc = execution_accuracy(pairs, s.db_path)
    n = len(rows)
    summary = {
        "n": n,
        "execution_accuracy": round(acc["execution_accuracy"], 4),
        "pred_execution_rate": round(acc["pred_execution_rate"], 4),
        "grounded_first_try": first_try,
        "repaired": repaired,
        "abstained": abstained,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2))
    logger.success("eval -> {}", args.out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
