"""Schema retrieval: pick the subset of tables relevant to a question and render a
focused schema string. On a 6-table toy DB the whole schema fits in the prompt, but
this is the mechanism that keeps prompts small as a schema grows — score tables by
keyword overlap with the question, then pull in their foreign-key neighbours so joins
remain expressible."""

from __future__ import annotations

import re

# table -> (columns, fk-neighbours)
TABLES: dict[str, tuple[list[str], list[str]]] = {
    "categories": (["category_id", "name", "description"], ["products"]),
    "customers": (
        ["customer_id", "first_name", "last_name", "email", "city", "country", "created_at"],
        ["orders", "reviews"],
    ),
    "products": (
        ["product_id", "name", "category_id", "price", "stock"],
        ["categories", "order_items", "reviews"],
    ),
    "orders": (
        ["order_id", "customer_id", "order_date", "status", "total"],
        ["customers", "order_items"],
    ),
    "order_items": (
        ["order_item_id", "order_id", "product_id", "quantity", "unit_price"],
        ["orders", "products"],
    ),
    "reviews": (
        ["review_id", "product_id", "customer_id", "rating", "comment", "review_date"],
        ["products", "customers"],
    ),
}
# words that hint at a table beyond its literal name
HINTS: dict[str, list[str]] = {
    "categories": ["category", "categories"],
    "customers": ["customer", "customers", "city", "country", "buyer", "client"],
    "products": ["product", "products", "price", "stock", "cost", "expensive", "cheap", "item"],
    "orders": [
        "order",
        "orders",
        "status",
        "delivered",
        "shipped",
        "pending",
        "cancelled",
        "revenue",
        "total",
    ],
    "order_items": ["item", "items", "quantity", "sold", "units"],
    "reviews": ["review", "reviews", "rating", "rated", "stars"],
}
_TOKEN = re.compile(r"[a-z0-9]+")


def relevant_tables(question: str, expand_fks: bool = True) -> list[str]:
    toks = set(_TOKEN.findall(question.lower()))
    scored = {t: sum(1 for h in HINTS[t] if h in toks) for t in TABLES}
    chosen = {t for t, s in scored.items() if s > 0}
    if not chosen:
        chosen = set(TABLES)  # nothing matched -> fall back to full schema
    if expand_fks:
        for t in list(chosen):
            chosen.update(TABLES[t][1])
    # stable order matching declaration
    return [t for t in TABLES if t in chosen]


def focused_schema(question: str) -> str:
    lines = ["Tables:"]
    for t in relevant_tables(question):
        cols = ", ".join(TABLES[t][0])
        lines.append(f"{t}({cols})")
    return "\n".join(lines)
