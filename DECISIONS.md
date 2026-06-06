# Design decisions

### One system, not three demos
SQLMender folds three techniques into a single pipeline. Text-to-SQL is the **task**;
LoRA fine-tuning is the **method** (the generator); retrieval + a self-correcting loop
is the **wrapper**. This reads as one coherent product rather than three disconnected
exercises, and every component pulls real weight at inference time.

### The database is the critic (execution-grounded self-healing)
The single most important choice. Rather than ask a model to grade its own SQL, the
agent **executes** the query and treats the result as ground truth: an execution error
or (optionally, once) an empty result is a concrete repair signal, and the error text
is fed back into the next generation. This is the self-healing-RAG idea made objective.

### Heuristic generator as baseline *and* sandbox/CI fallback
A deterministic question→SQL pattern engine (`llm/generator.py`) runs with no model, so
the agent, API, and tests are fully exercisable anywhere — and it serves as the honest
baseline the fine-tuned model is measured against. `get_generator()` returns the MLX
fine-tuned model when MLX + a trained adapter are present, otherwise the heuristic. Same
agent code, two environments. The heuristic also performs a *real* repair: given a
"no such column" error it swaps in the correct column from a synonym map.

### Runnable vs. correct — two different metrics, reported separately
The loop guarantees a query that **executes** (or an abstention); it does **not** by
itself guarantee correctness. So we report both: predicted-execution-rate (100% with the
heuristic) *and* execution accuracy vs. gold (16.3% heuristic baseline). Conflating them
would overstate the system. Keeping them separate is the honest framing and motivates the
fine-tune.

### Safe, read-only executor
All execution goes through a SELECT-only guard (`sql/executor.py`) backed by sqlglot
parsing, a statement-type check, a row cap, and a timeout. `/sql` exposes direct
execution but only for read-only SELECTs; mutations are rejected with 400. The agent
catches `UnsafeQueryError` and routes it through the same critic as any other failure.

### Retrieval that scales beyond a toy schema
On six tables the whole schema fits in the prompt, but `retrieval/schema_index.py` still
selects a relevant table subset (keyword overlap + foreign-key expansion) — the mechanism
that keeps prompts small as schemas grow. `retrieval/example_index.py` adds BM25 few-shot
retrieval so the model sees the project's exact SQL style.

### Prompt parity between training and inference
`train/prompt.py` defines the base format used to build the fine-tuning data; the agent
prompt (`llm/prompts.py`) builds on that identical base and only *adds* (few-shots, a
repair note). A train/inference format mismatch silently destroys accuracy, so they share
one source of truth.

### Dataset built by templates + paraphrase, every pair execution-validated
Training pairs come from parameterized SQL templates over the real schema, lightly
paraphrased for surface variety; **every** pair is executed against the DB and dropped if
it fails (`data_gen.validate_executes`). The result is 1,414 pairs with zero
non-executing queries — quality over raw count.

### LangGraph for the agent
The loop is a compiled `StateGraph` with dependency-injected generator/critic/executor/
index, so production wires real backends and tests inject fakes to drive the happy,
repair, and abstain paths deterministically.

### Same-origin dashboard
`api/main.py` mounts the dashboard as static files (mounted last so API routes win), so
`uvicorn sqlmender.api.main:app` serves both UI and API with no gateway and no CORS.

---

### Note on commit history
This repository was assembled in a sandbox that could not run MLX/GPU. The commit
sequence reflects the **logical build order** (scaffold → data → SQL tooling → metric →
retrieval → generator/critic → agent → API → frontend → tests → docs) using Conventional
Commits. Messages are reconstructions of that order, not a keystroke-level history; they
can be reworded with `git rebase -i --root` if a specific message set is required.
