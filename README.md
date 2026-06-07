# SQLMender

> **A self-correcting, fine-tuned Natural-Language-to-SQL agent.**  
> Ask a question in plain English — SQLMender retrieves context, generates SQL, executes it, and heals itself on failure. The database is the critic.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-0.2+-FF6F00?style=for-the-badge&logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/MLX-Apple_Silicon-black?style=for-the-badge&logo=apple&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-56_passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" />
  <img src="https://img.shields.io/badge/Coverage-79%25-yellowgreen?style=for-the-badge" />
</p>

---

## What is SQLMender?

SQLMender unifies **three AI techniques** into one end-to-end system:

| Layer | Technique | Purpose |
|---|---|---|
| **Retrieval** | BM25 few-shot + schema subset selection | Ground the prompt with relevant examples & tables |
| **Generation** | Fine-tuned 4-bit Qwen2.5-3B (MLX LoRA, rank 16) | Produce candidate SQL |
| **Self-Correction** | LangGraph agentic loop with execution feedback | Heal bad queries or abstain honestly |

The core insight: **the database is the critic.** Instead of asking an LLM to grade its own output, SQLMender executes the SQL against a real SQLite database and feeds execution errors directly back into the next generation step.

---

## Architecture

### System Overview

```mermaid
graph TB
    User["👤 User / API Client"]
    Auth["🔐 JWT Auth\n/auth/token"]
    API["⚡ FastAPI\n/ask  /sql  /schema"]
    UI["🖥️ Dashboard\nfrontend/index.html"]

    subgraph Agent ["🤖 Self-Healing Agent (LangGraph)"]
        direction LR
        Retrieve["📚 Retrieve\nBM25 few-shot\n+ schema subset"]
        Generate["🧠 Generate\nHeuristic or\nMLX Qwen2.5-3B"]
        Execute["▶️ Execute\nRead-only SQLite\n(5s timeout)"]
        Critic["⚖️ Critic\nExecution-grounded\nfeedback"]
        Abstain["🚫 Abstain\nHonest fallback"]
    end

    subgraph Retrieval ["🔍 Retrieval Layer"]
        BM25["BM25 Index\n(1,273 examples)"]
        SchemaIdx["Schema Selector\n(6 tables → subset)"]
    end

    subgraph LLM ["🤖 Generator Backends"]
        Heuristic["HeuristicGenerator\n(runs everywhere)"]
        MLX["MLXGenerator\n(Apple Silicon only)"]
    end

    subgraph DB ["🗄️ SQLite Database"]
        EcommDB["ecommerce.db\ncategories · customers\nproducts · orders\norder_items · reviews"]
    end

    User -->|"plain English question"| API
    User --> Auth
    Auth -->|"bearer token"| API
    API --> Agent
    API --> UI
    Retrieve --> BM25
    Retrieve --> SchemaIdx
    Generate --> Heuristic
    Generate --> MLX
    Execute --> DB
    Critic --> DB
    Retrieve --> Generate
    Generate --> Execute
    Execute --> Critic
    Critic -->|"✅ grounded"| API
    Critic -->|"🔁 repair: error injected"| Generate
    Critic -->|"❌ max attempts"| Abstain
    Abstain --> API
```

### Agent Self-Correction Loop

```mermaid
flowchart LR
    START([START]) --> R["📚 Retrieve\nfew-shots + schema"]
    R --> G["🧠 Generate SQL"]
    G --> E["▶️ Execute\nagainst SQLite"]
    E --> C{"⚖️ Critic"}

    C -->|"✅ result ok\nor accepted"| END(["END — return answer"])
    C -->|"❌ error / empty\nattempts left"| H["💉 Inject error\ninto prompt"]
    H --> G
    C -->|"❌ max attempts\nexhausted"| A["🚫 Abstain"]
    A --> END

    style START fill:#22c55e,color:#fff
    style END fill:#3b82f6,color:#fff
    style A fill:#ef4444,color:#fff
    style C fill:#f59e0b,color:#fff
```

### Request Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant A as Agent
    participant R as Retriever (BM25)
    participant G as Generator
    participant E as Executor
    participant DB as SQLite

    U->>API: POST /ask {"question": "..."}
    API->>A: ask(question)
    A->>R: retrieve(question, k=3)
    R-->>A: few-shot examples + schema subset
    A->>G: generate(question, few_shots, hint=None)
    G-->>A: candidate SQL
    A->>E: execute(sql)
    E->>DB: SELECT ... (read-only, 5s timeout)
    DB-->>E: rows / error
    E-->>A: QueryResult

    alt Execution error or empty result
        A->>G: generate(question, few_shots, hint=error_msg)
        G-->>A: repaired SQL
        A->>E: execute(repaired_sql)
        E->>DB: SELECT ...
        DB-->>E: rows
        E-->>A: QueryResult
    end

    alt Max attempts exceeded
        A-->>API: abstain("I couldn't produce a correct query")
    else SQL executes correctly
        A-->>API: AskResponse(sql, rows, repair_history)
    end

    API-->>U: JSON response
```

---

## Database Schema

The synthetic e-commerce database (`data/ecommerce.db`):

```mermaid
erDiagram
    categories {
        int id PK
        text name
    }
    customers {
        int id PK
        text name
        text email
        text city
        text country
    }
    products {
        int id PK
        text name
        real price
        int stock
        int category_id FK
    }
    orders {
        int id PK
        int customer_id FK
        date order_date
        text status
        real total_amount
    }
    order_items {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        real unit_price
    }
    reviews {
        int id PK
        int customer_id FK
        int product_id FK
        int rating
        text comment
    }

    categories ||--o{ products : "has"
    customers ||--o{ orders : "places"
    customers ||--o{ reviews : "writes"
    products ||--o{ order_items : "included in"
    products ||--o{ reviews : "receives"
    orders ||--o{ order_items : "contains"
```

**Record counts** (deterministic seed): categories: 8 · customers: 210 · products: 220 · orders: 300 · order_items: 746 · reviews: 250

---

## Features

- **Self-healing agent** — Automatically repairs SQL on execution errors (up to 3 attempts)
- **Execution-grounded feedback** — Database errors drive correction, not LLM self-grading
- **BM25 few-shot retrieval** — Semantically relevant examples from 1,273 training pairs
- **Schema subset selection** — Only relevant tables fed to the model (scales beyond toy schemas)
- **Dual generator backends** — MLX fine-tuned model on Apple Silicon; deterministic heuristic everywhere else
- **Multi-layer SQL safety** — sqlglot AST check + SQLite read-only file URI + 5s timeout + 1000-row cap
- **Production-ready API** — FastAPI with JWT auth, health check, schema endpoint
- **Dark agent console** — Single-file dashboard with live self-healing trace viewer
- **79% test coverage** — 56 tests across all agent paths, API, retrieval, SQL safety

---

## Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.11+ |
| **API Framework** | FastAPI 0.111+, Uvicorn 0.30+ |
| **Agent Framework** | LangGraph 0.2+, LangChain Core 0.3+ |
| **SQL Parsing** | sqlglot 25.0+ |
| **Retrieval** | rank-bm25 0.2.2+ |
| **Validation** | Pydantic 2.7+, pydantic-settings 2.3+ |
| **Auth** | python-jose[cryptography] 3.3+ (JWT) |
| **Logging** | loguru 0.7.2+ |
| **ML (Apple Silicon)** | MLX 0.18+, mlx-lm 0.18+ |
| **Base Model** | Qwen2.5-3B-4bit (LoRA rank 16, lr 1e-5, 600 iters) |
| **Testing** | pytest 8.2+, pytest-cov 5.0+, httpx 0.27+ |
| **Linting** | ruff 0.4+, black 24.4+ |
| **Database** | SQLite (e-commerce schema, deterministic seed) |
| **Frontend** | Vanilla HTML/CSS/JS (single file, dark theme) |

---

## Quickstart

### Prerequisites

- Python 3.11+
- macOS with Apple Silicon (optional, for MLX fine-tuning)

### Install & Run

```bash
# 1. Clone the repo
git clone https://github.com/AshuGuptaz/SqlMendor.git
cd SqlMendor

# 2. Install dependencies
make install          # creates venv, editable install, dev tools

# 3. Build the database and dataset
make data             # ecommerce.db + 1,414 NL-SQL pairs + MLX prep files

# 4. Start the API + dashboard
make dev              # → http://localhost:8000
```

### Fine-tuning (Apple Silicon M1/M2/M3)

```bash
make train            # LoRA fine-tune: Qwen2.5-3B-4bit, rank 16, 600 iters
make eval             # run agent over 141 test examples → outputs/eval.json
```

When a trained adapter is present and MLX is importable, the agent automatically switches to the fine-tuned model. Otherwise it falls back to the **heuristic generator** — the full pipeline (API, tests, agent loop) runs anywhere.

---

## Usage

### Dashboard

Open **http://localhost:8000** after `make dev` for the interactive dark console with live self-healing trace.

### REST API

**1. Get a token:**
```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/token \
  -d "username=demo&password=demo-password" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

**2. Ask a question:**
```bash
curl -s -X POST localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 most expensive products?"}' \
  | python -m json.tool
```

**Sample Response:**
```json
{
  "sql": "SELECT name, price FROM products ORDER BY price DESC LIMIT 5",
  "columns": ["name", "price"],
  "rows": [["UltraWidget Pro", 499.99], ["..."]],
  "attempts": 1,
  "status": "ok",
  "history": []
}
```

**3. Direct SQL execution:**
```bash
curl -s -X POST localhost:8000/sql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) FROM orders WHERE status = '\''completed'\''"}' \
  | python -m json.tool
```

### API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET`  | `/health` | — | Liveness probe |
| `GET`  | `/schema` | JWT | Returns full schema description |
| `POST` | `/ask` | JWT | Self-healing NL→SQL agent |
| `POST` | `/sql` | JWT | Direct read-only SELECT execution |
| `POST` | `/auth/token` | — | Demo login → bearer token |

---

## Results & Metrics

| Metric | Heuristic baseline | Fine-tuned MLX (Qwen2.5-3B) |
|---|---|---|
| **Execution accuracy** | 16.3% | **53.9%** |
| Predicted-query execution rate | 100% | 56.0% |
| Grounded on first try | 141 / 141 | 46 / 141 |
| Repaired successfully | 0 | 33 / 141 |
| Abstained (honest) | 0 | 62 / 141 |
| **Dataset** | 1,414 pairs (1,273 train / 141 test), 0 non-executing | — |
| **Test suite** | 56 passing, 79% coverage | — |
| **Training** | — | rank 16 LoRA, 600 iters, 2.7GB peak, Apple M1 |

**+37.6 percentage points lift** from fine-tuning (16.3% → 53.9%).

> Abstentions are intentional — the agent declines rather than return wrong SQL. The repair loop salvaged 33 queries that failed on first attempt.

---

## Project Structure

```
sqlmender/
├── src/sqlmender/
│   ├── config.py              # Pydantic settings (DB path, LoRA params, agent config)
│   ├── schemas.py             # API request/response models
│   ├── db/
│   │   ├── build_db.py        # Builds SQLite with deterministic seed
│   │   ├── seed.py            # Data generation
│   │   └── schema_info.py     # Human-readable schema description
│   ├── sql/
│   │   ├── normalizer.py      # sqlglot AST parsing & normalization
│   │   └── executor.py        # Multi-layer read-only executor
│   ├── retrieval/
│   │   ├── example_index.py   # BM25 few-shot retrieval
│   │   └── schema_index.py    # Relevant table subset selection
│   ├── llm/
│   │   ├── prompts.py         # Agent prompt construction
│   │   ├── generator.py       # HeuristicGenerator + MLXGenerator
│   │   └── critic.py          # Execution-grounded verdict
│   ├── agent/
│   │   ├── state.py           # LangGraph AgentState TypedDict
│   │   ├── nodes.py           # retrieve / generate / execute / critic / abstain
│   │   ├── edges.py           # Conditional routing logic
│   │   └── graph.py           # LangGraph assembly + ask() entrypoint
│   ├── train/
│   │   ├── templates.py       # SQL template families (8 categories)
│   │   ├── data_gen.py        # 1,414 NL-SQL pairs with paraphrasing
│   │   ├── prompt.py          # Shared train/inference prompt format
│   │   ├── prepare_mlx.py     # Convert JSONL → MLX format
│   │   ├── train.py           # LoRA fine-tuning (Apple Silicon)
│   │   └── infer.py           # Inference with trained adapter
│   ├── eval/
│   │   └── metrics.py         # Execution accuracy (order-insensitive)
│   └── api/
│       ├── auth.py            # JWT creation/verification
│       ├── routes.py          # FastAPI endpoints
│       └── main.py            # App factory + frontend mount
├── frontend/
│   └── index.html             # Dark agent console (22KB, single file)
├── tests/                     # 56 tests, 79% coverage
│   ├── test_agent.py          # Happy/repair/abstain paths
│   ├── test_api.py            # Endpoint integration + JWT
│   ├── test_executor_safety.py # Rejects INSERT/UPDATE/DELETE/DROP
│   ├── test_normalizer.py
│   ├── test_retrieval.py
│   ├── test_generator.py
│   ├── test_metrics.py
│   └── ...
├── scripts/
│   └── run_eval.py            # Evaluation runner → outputs/eval.json
├── data/
│   ├── ecommerce.db           # Built by `make data`
│   ├── train.jsonl            # 1,273 training pairs
│   └── test.jsonl             # 141 test pairs
├── adapters/sql-lora/         # Trained LoRA weights (Apple Silicon)
├── outputs/
│   ├── eval.json              # Evaluation results
│   └── RESULTS.md             # Measured metrics
├── Makefile                   # All commands (install/data/train/eval/test/dev)
├── pyproject.toml             # Dependencies + project metadata
├── DECISIONS.md               # Design decisions & trade-offs
├── BLOCKERS.md                # Environment gates (MLX, external LLM)
└── PROGRESS.md                # Build log + acceptance checklist
```

---

## Design Decisions

See [DECISIONS.md](DECISIONS.md) for full context. Key choices:

1. **Database as critic** — Real execution errors drive repair, not LLM self-grading
2. **Heuristic baseline + MLX upgrade** — Full pipeline works everywhere; fine-tune is a drop-in upgrade
3. **Runnable ≠ correct** — Execution rate and accuracy reported separately
4. **Multi-layer SQL safety** — sqlglot AST + read-only SQLite URI + timeout + row cap
5. **Prompt parity** — `train/prompt.py` shared between training and inference
6. **Execution-validated dataset** — Every training pair tested against the real DB (0 broken pairs)
7. **LangGraph state graph** — Compiled graph with dependency injection for testability
8. **Same-origin dashboard** — Uvicorn serves both API and UI, no CORS complexity

---

## Make Commands

```bash
make install    # Create venv, editable install, dev dependencies
make data       # Build DB, generate 1,414 NL-SQL pairs, prep MLX files
make train      # LoRA fine-tune on Apple Silicon (MLX required)
make eval       # Run agent over test set → outputs/eval.json
make test       # Run 56 tests with coverage report
make lint       # ruff check
make fmt        # black + ruff --fix
make dev        # Start API server at http://localhost:8000
```

---

## License

MIT

---

<p align="center">
  Built with LangGraph · MLX · FastAPI · sqlglot · BM25
</p>
