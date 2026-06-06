# Progress log

Build order (Conventional Commits). One logical step per commit.

1. `chore: scaffold sqlmender package, pyproject, tooling config`
2. `feat(config): settings for db, LoRA, executor, agent, retrieval`
3. `feat(schemas): pydantic models incl. agent ask/response + repair steps`
4. `feat(db): schema, deterministic seed, build script, schema_info`
5. `feat(sql): sqlglot normalizer + safe read-only executor`
6. `feat(eval): execution-accuracy metric (result-set comparison)`
7. `feat(data): SQL templates + execution-validated dataset generator`
8. `feat(train): shared prompt, MLX data prep, LoRA train + infer (Apple Silicon)`
9. `feat(retrieval): BM25 few-shot index + schema-subset selection`
10. `feat(llm): agent prompts, heuristic+MLX generators, execution-grounded critic`
11. `feat(agent): cyclical LangGraph self-healing loop (retrieve→generate→execute→critic→repair/abstain)`
12. `feat(api): FastAPI routes (/ask, /sql, /schema, /auth) + JWT + dashboard mount`
13. `feat(frontend): dark agent console with live self-healing trace + demo fallback`
14. `test: 56 tests across sql, retrieval, agent paths, api, generator, prompts`
15. `feat(eval): run_eval script -> outputs/eval.json (heuristic baseline)`
16. `docs: README, DECISIONS, BLOCKERS, RESULTS, PROGRESS`

---

## Acceptance checklist

| Criterion | Status | Evidence |
|---|---|---|
| Database builds with realistic rows | ✅ PASS | categories 8 · customers 210 · products 220 · orders 300 · order_items 746 · reviews 250 |
| Dataset generated, **every query executes** | ✅ PASS | 1,414 pairs (1,273 train / 141 test), 0 non-executing |
| SQL normalizer equivalence/parse checks | ✅ PASS | `tests/test_normalizer.py` |
| Executor rejects all mutations, caps rows | ✅ PASS | `tests/test_executor_safety.py` (INSERT/UPDATE/DELETE/DROP/ALTER/CREATE → raise) |
| Execution-accuracy metric | ✅ PASS | `tests/test_metrics.py` (order-insensitive, unsafe→0) |
| Few-shot + schema retrieval | ✅ PASS | `tests/test_retrieval.py` |
| Self-healing **repair** (error→fix→ground) | ✅ PASS | `tests/test_agent.py::test_repair_path_fixes_then_grounds` + live `total_price→unit_price` demo |
| **Abstain** after max attempts | ✅ PASS | `tests/test_agent.py::test_abstains_after_max_attempts` |
| Happy path grounds on first try | ✅ PASS | `tests/test_agent.py::test_happy_path_grounds_first_try` |
| API `/ask` end-to-end + JWT gating | ✅ PASS | `tests/test_api.py`; live TestClient against real DB returns SQL+rows; 401 without token |
| Dashboard served same-origin | ✅ PASS | `GET /` → 200 HTML; `/health`,`/schema` routes take precedence |
| ≥15 tests, healthy coverage | ✅ PASS | **56 passing, 79%** |
| Lint/format clean | ✅ PASS | ruff + black clean |
| Heuristic baseline execution accuracy | ✅ PASS | **16.3%**, 100% execution rate (`outputs/eval.json`) |
| Fine-tuned (MLX) accuracy & loss | ⏳ PARTIAL | ⟳ run `make train && make eval` on Apple Silicon (see BLOCKERS.md) |

Legend: ✅ done & verified · ⏳ gated on Apple Silicon / external services (honest placeholder, nothing fabricated).
