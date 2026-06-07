# Results

## Heuristic baseline — Linux/CPU

From `scripts/run_eval.py` over the 141-example held-out test set:

| Metric | Value |
|---|---|
| Test examples | 141 |
| Execution accuracy (vs. gold) | **16.3%** |
| Predicted-query execution rate | **100%** |
| Grounded on first try | 141 |
| Repaired | 0 |
| Abstained | 0 |

> The heuristic always emits a runnable query so the loop never repairs or abstains —
> but it's only the correct query ~16% of the time.

---

## Fine-tuned model — MLX LoRA (Qwen2.5-3B-4bit, rank 16, 600 iters, Apple M1)

| Metric | Value |
|---|---|
| Test examples | 141 |
| **Execution accuracy (vs. gold)** | **53.9%** |
| Predicted-query execution rate | **56.0%** |
| Grounded on first try | 46 |
| Repaired successfully | 33 |
| Abstained (honest) | 62 |
| Final train loss | 0.038 |
| Final val loss | 0.034 |
| Peak GPU memory | 2.746 GB |

**Lift over heuristic baseline: +37.6 percentage points (16.3% → 53.9%)**

> Abstentions are intentional — the agent declines rather than return wrong SQL.
> The repair loop salvaged 33 queries that failed on first attempt.

---

## Test suite

**56 tests passing, 79% line coverage.** Dataset: **1,414 pairs, 0 non-executing.**
