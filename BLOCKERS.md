# Blockers & environment notes

Everything that could run truthfully on Linux/CPU was run for real. The items below are
gated by hardware or external services and are left as explicit, honest placeholders —
**no metrics are fabricated.**

### 1. MLX LoRA training & inference — Apple Silicon only
`mlx` / `mlx-lm` require Apple Silicon (Metal) and cannot import on Linux/x86. So:
- `train/train.py`, `train/infer.py`, and `llm/generator.MLXGenerator` are **not executed
  here** (and show 0% line coverage — by design; they're marked/optional).
- The fine-tuned model's **execution accuracy and training loss are `⟳ run`** in
  RESULTS.md / the dashboard. Run `make train && make eval` on your M1 to populate them.
- The MLX dependencies are environment-gated in `pyproject.toml` (`platform_system ==
  'Darwin' and platform_machine == 'arm64'`), so `make install` succeeds on Linux/CI.

Mitigation: the deterministic `HeuristicGenerator` runs the **entire** agent (retrieve →
generate → execute → critique → repair/abstain), the API, and the tests anywhere, and is
the baseline the fine-tune is compared against. The agent transparently upgrades to the
MLX model once it's available.

### 2. Teacher-LLM data augmentation — skipped (no external key)
The dataset is built from templates + light paraphrasing, with every pair
execution-validated. A teacher LLM (e.g. for harder, more natural questions) was **not**
used; it would slot into `train/data_gen.py` behind a key, and its outputs would pass the
same execution filter before inclusion.

### 3. Filesystem doesn't persist to the user's machine
Built as a self-contained, runnable tarball. Generated artifacts (`data/*.db`, `*.jsonl`,
MLX files) are reproducible with `make data`; the trained adapter with `make train`.
