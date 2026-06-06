"""SQL generators.

Three interchangeable backends behind one ``Generator`` protocol:

  * ``MLXGenerator``   — fine-tuned 4-bit Qwen + LoRA adapter (Apple Silicon).
  * ``GroqGenerator``  — real LLM via Groq's fast inference API (requires GROQ_API_KEY).
  * ``HeuristicGenerator`` — deterministic pattern engine; runs anywhere; the baseline.

Priority order in ``get_generator``: MLX → Groq → Heuristic.
"""

from __future__ import annotations

import re
from typing import Protocol

from sqlmender.config import Settings, get_settings
from sqlmender.schemas import SQLExample
from sqlmender.train.templates import CATEGORIES, CITIES, COUNTRIES, STATUSES


class Generator(Protocol):
    def generate(
        self,
        question: str,
        few_shots: list[SQLExample] | None = None,
        repair_hint: tuple[str, str] | None = None,
    ) -> str: ...


# --- common column-name repairs (model/heuristic mistakes -> real columns) ---
COLUMN_SYNONYMS = {
    "total_price": "unit_price",
    "totalprice": "unit_price",
    "amount": "unit_price",
    "qty": "quantity",
    "fname": "first_name",
    "lname": "last_name",
    "product_name": "name",
    "customer_name": "first_name",
    "cost": "price",
    "rating_score": "rating",
    "country_name": "country",
    "city_name": "city",
}

_NUM = re.compile(r"\b(\d+)\b")


def _find(question: str, options: list[str]) -> str | None:
    q = question.lower()
    for opt in options:
        if opt.lower() in q:
            return opt
    return None


def _num(question: str, default: int = 5) -> int:
    m = _NUM.search(question)
    return int(m.group(1)) if m else default


class HeuristicGenerator:
    """Deterministic question -> SQL for common patterns; real column repair."""

    name = "heuristic"

    def generate(self, question, few_shots=None, repair_hint=None) -> str:
        if repair_hint is not None:
            fixed = self._repair(repair_hint)
            if fixed is not None:
                return fixed
        return self._match(question)

    def _repair(self, repair_hint: tuple[str, str]) -> str | None:
        bad_sql, error = repair_hint
        m = re.search(r"no such column:\s*([A-Za-z0-9_.]+)", error)
        if not m:
            return None
        col = m.group(1).split(".")[-1]
        if col in COLUMN_SYNONYMS:
            return re.sub(rf"\b{re.escape(col)}\b", COLUMN_SYNONYMS[col], bad_sql)
        return None

    def _match(self, question: str) -> str:
        q = question.lower()
        cat = _find(question, CATEGORIES)
        city = _find(question, CITIES)
        country = _find(question, COUNTRIES)
        status = _find(question, STATUSES)

        if "out of stock" in q:
            return "SELECT COUNT(*) FROM products WHERE stock = 0;"
        if "distinct" in q and "status" in q:
            return "SELECT DISTINCT status FROM orders;"
        if "distinct" in q and ("country" in q or "countries" in q):
            return "SELECT DISTINCT country FROM customers;"
        if ("most expensive" in q or "highest price" in q) and "product" in q:
            n = 1 if "the most expensive product" in q else _num(question, 5)
            return f"SELECT name, price FROM products ORDER BY price DESC LIMIT {n};"
        if "cheapest" in q and "product" in q:
            return f"SELECT name, price FROM products ORDER BY price ASC LIMIT {_num(question, 5)};"
        if "how many" in q and "order" in q and status:
            return f"SELECT COUNT(*) FROM orders WHERE status = '{status}';"
        if ("revenue" in q or "total" in q) and "order" in q:
            if status:
                return f"SELECT SUM(total) FROM orders WHERE status = '{status}';"
            return "SELECT SUM(total) FROM orders;"
        if "how many customers" in q and country:
            return f"SELECT COUNT(*) FROM customers WHERE country = '{country}';"
        if "customers" in q and city:
            return f"SELECT first_name, last_name FROM customers WHERE city = '{city}';"
        if "average" in q and "price" in q and cat:
            return (
                "SELECT AVG(p.price) FROM products p JOIN categories c "
                f"ON p.category_id = c.category_id WHERE c.name = '{cat}';"
            )
        if "average" in q and "price" in q:
            return "SELECT AVG(price) FROM products;"
        if "less than" in q and "product" in q:
            return f"SELECT name, price FROM products WHERE price < {_num(question, 50)};"
        if ("more than" in q or "over" in q) and "product" in q:
            return f"SELECT name, price FROM products WHERE price > {_num(question, 100)};"
        if "products" in q and cat:
            return (
                "SELECT p.name FROM products p JOIN categories c "
                f"ON p.category_id = c.category_id WHERE c.name = '{cat}';"
            )
        if "how many reviews" in q and "rating" in q:
            return f"SELECT COUNT(*) FROM reviews WHERE rating = {_num(question, 5)};"
        if "how many products" in q and "each category" in q:
            return (
                "SELECT c.name, COUNT(*) AS n FROM products p JOIN categories c "
                "ON p.category_id = c.category_id GROUP BY c.name;"
            )
        if "low stock" in q or (
            "stock" in q and ("less than" in q or "below" in q or "fewer" in q)
        ):
            return f"SELECT name, stock FROM products WHERE stock < {_num(question, 50)};"
        # no confident match: a safe, generic answer the critic can still evaluate
        return "SELECT name, price FROM products ORDER BY price DESC LIMIT 5;"


_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _clean_sql(text: str) -> str:
    """Strip markdown fences and normalise to a single-line SQL string."""
    m = _SQL_FENCE.search(text)
    if m:
        text = m.group(1)
    text = text.strip().strip("`").strip()
    sql = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if sql and not sql.endswith(";"):
        sql += ";"
    return sql


class GroqGenerator:
    """Real LLM SQL generation via Groq's fast inference API."""

    name = "groq"

    def __init__(self, settings: Settings | None = None):
        import groq

        s = settings or get_settings()
        self._client = groq.Groq(api_key=s.groq_api_key)
        self._model = s.groq_model

    def generate(self, question, few_shots=None, repair_hint=None) -> str:
        from sqlmender.llm.prompts import build_agent_prompt

        prompt = build_agent_prompt(question, few_shots, repair_hint)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a SQL expert. Return ONLY a valid SQLite SELECT query — "
                        "no explanation, no markdown, no extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        return _clean_sql(raw)


class MLXGenerator:
    """Fine-tuned 4-bit Qwen + LoRA adapter (Apple Silicon)."""

    name = "mlx-lora"

    def __init__(self, settings: Settings | None = None):
        from sqlmender.train.infer import SQLGenerator

        self._gen = SQLGenerator(settings or get_settings())

    def generate(self, question, few_shots=None, repair_hint=None) -> str:
        from sqlmender.llm.prompts import build_agent_prompt

        prompt = build_agent_prompt(question, few_shots, repair_hint)
        # SQLGenerator builds its own base prompt; reuse its model via the rich prompt.
        self._gen._ensure_loaded()
        from mlx_lm import generate as mlx_generate
        from mlx_lm.sample_utils import make_sampler

        from sqlmender.train.infer import _clean_sql

        out = mlx_generate(
            self._gen._model,
            self._gen._tok,
            prompt=prompt,
            max_tokens=256,
            sampler=make_sampler(temp=0.0),
            verbose=False,
        )
        return _clean_sql(out)


def mlx_available(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    try:
        import mlx_lm  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    from pathlib import Path

    return Path(s.adapter_path).exists()


def groq_available(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    if not s.groq_api_key:
        return False
    try:
        import groq  # noqa: F401
    except ImportError:
        return False
    return True


def get_generator(settings: Settings | None = None) -> Generator:
    s = settings or get_settings()
    if mlx_available(s):
        return MLXGenerator(s)
    if groq_available(s):
        return GroqGenerator(s)
    return HeuristicGenerator()
