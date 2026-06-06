# Results

## Measured here — Linux/CPU, heuristic generator baseline (REAL)
From `scripts/run_eval.py` over the 141-example held-out test set (`outputs/eval.json`):

| Metric | Value |
|---|---|
| Test examples | 141 |
| Execution accuracy (vs. gold) | **0.163 (16.3%)** |
| Predicted-query execution rate | **1.000** |
| Grounded on first try | 141 |
| Repaired | 0 |
| Abstained | 0 |

Suite: **56 tests passing, 79% line coverage.** Dataset: **1,414 pairs, 0 non-executing.**

> The heuristic always emits a runnable query, so the loop never needs to repair or
> abstain *on this baseline* — but it's only the correct query ~16% of the time. The
> repair and abstain paths are proven separately in `tests/test_agent.py` and by the
> live demo (a `total_price → unit_price` correction, and a 2031-World-Cup abstention).

## Fine-tuned model (MLX LoRA, rank 16) — ⟳ RUN ON APPLE SILICON
Populate by running on an M1/M2/M3 Mac:

```bash
make train        # writes adapters/sql-lora/
make eval         # rewrites outputs/eval.json with the fine-tuned generator
```

| Metric | Value |
|---|---|
| Final train / val loss | `<run make train>` |
| Execution accuracy (fine-tuned) | `<run make eval>` |
| Lift over heuristic baseline | `<run>` |

No numbers are invented; these remain placeholders until the run completes.
