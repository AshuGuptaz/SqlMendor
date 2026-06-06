# SQLMender

**A self-correcting, fine-tuned natural-language-to-SQL agent.** Ask a question in
plain English; SQLMender retrieves the relevant schema and similar examples,
generates SQL with a fine-tuned Qwen, runs it against a real SQLite database, and —
if the query errors or comes back empty — reads the failure and repairs the query,
or abstains rather than return something wrong.

It unifies three techniques into one end-to-end system:

| Ingredient | Role in SQLMender |
|---|---|
| **MLX LoRA fine-tuning** (4-bit Qwen2.5-3B, rank 16) | the **generator** |
| **Retrieval** (schema subset + BM25 few-shot examples) | **grounds** the prompt |
| **Agentic self-correction** (cyclical LangGraph loop) | **heals** bad queries / abstains |

---

## The idea: the database is the critic

Most "agentic" loops ask a model to grade itself. SQLMender doesn't — it **executes
the SQL** and lets the database be the oracle:

```
START → retrieve → generate → execute → critique
                       ▲                    │
                       │   (repair: feed     │  grounded → END
                       │    the error back)  ▼
                       └──────────────── route ──→ abstain → END
```

* **error** (bad column/table, syntax) → repair, with the execution error injected
  into the next prompt
* **empty result** → one informed retry, then accept (an empty answer can be correct)
* **out of attempts** (default 3) → **abstain** with an honest "I couldn't answer"

This makes the self-correction signal *real* rather than a model's opinion.

## Quickstart

```bash
make install          # venv + editable install (+ dev tools)
make data             # build the SQLite DB, generate the dataset, prep MLX files
make dev              # serve the API + dashboard at http://localhost:8000
```

Open **http://localhost:8000** for the dashboard, or hit the API:

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/token \
  -d "username=demo&password=demo-password" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -X POST localhost:8000/ask -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the total value of all order items?"}' | python -m json.tool
```

### API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET  | `/health` | — | liveness |
| GET  | `/schema` | JWT | schema description |
| POST | `/ask` | JWT | run the self-healing agent |
| POST | `/sql` | JWT | execute a provided read-only SELECT (no model) |
| POST | `/auth/token` | — | demo login → bearer token |

## Fine-tuning (Apple Silicon)

```bash
make train            # MLX LoRA: rank 16, lr 1e-5, 600 iters, batch 1
make eval             # agent over the test set → outputs/eval.json
```

When a trained adapter is present and MLX is importable, the agent automatically
uses the fine-tuned model; otherwise it falls back to a deterministic **heuristic
generator** so the loop, the API, and the tests run anywhere (it's also the baseline).

## Database

A synthetic e-commerce store (deterministic seed): `categories`, `customers`,
`products`, `orders`, `order_items`, `reviews` — with foreign keys and realistic
distributions, so aggregates and joins return meaningful results.

## Results

Measured here (Linux/CPU, **heuristic** generator baseline):

| Metric | Value |
|---|---|
| Dataset | **1,414 pairs** (1,273 train / 141 test), **0 non-executing** |
| Tests | **56 passing**, **79%** coverage |
| Execution accuracy (heuristic baseline) | **16.3%** |
| Predicted-query execution rate | **100%** (loop guarantees runnable SQL or abstain) |
| Fine-tuned (MLX) execution accuracy | **⟳ run `make train && make eval` on M1** |

> **Runnable ≠ correct.** The loop guarantees the agent returns SQL that *executes*
> (or abstains); **execution accuracy** measures whether it's the *right* query. The
> 16% baseline is precisely the gap the fine-tuned model is there to close — run it
> on your M1 to populate the number.

## Layout

```
src/sqlmender/
  config.py schemas.py
  db/         schema.sql · seed.py · build_db.py · schema_info.py
  sql/        normalizer.py (sqlglot) · executor.py (safe, read-only)
  retrieval/  example_index.py (BM25 few-shot) · schema_index.py (table subset)
  llm/        prompts.py · generator.py (heuristic + MLX) · critic.py (execution-grounded)
  agent/      state.py · nodes.py · edges.py · graph.py (LangGraph)
  train/      templates.py · data_gen.py · prompt.py · prepare_mlx.py · train.py · infer.py
  eval/       metrics.py (execution accuracy)
  api/        auth.py · routes.py · main.py (also serves the dashboard)
frontend/index.html      scripts/run_eval.py      tests/  (56 tests)
```

See **DECISIONS.md** (design choices), **BLOCKERS.md** (what's M1-gated and why), and
**PROGRESS.md** (build log + acceptance checklist).
