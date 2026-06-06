"""Agent-side prompt construction.

Builds on the SAME base format the model is fine-tuned with (``train.prompt``) so
inference matches training, then layers on the two agent ingredients:
  * retrieved few-shot examples (question -> SQL) for in-context grounding, and
  * a repair note carrying the previous attempt's SQL and execution error, so a
    retry is informed rather than a blind re-roll.
"""

from __future__ import annotations

from sqlmender.retrieval.schema_index import focused_schema
from sqlmender.schemas import SQLExample
from sqlmender.train.prompt import INSTRUCTION


def build_agent_prompt(
    question: str,
    few_shots: list[SQLExample] | None = None,
    repair_hint: tuple[str, str] | None = None,
) -> str:
    parts = [INSTRUCTION, ""]
    parts.append("### Schema:")
    parts.append(focused_schema(question))
    parts.append("")
    if few_shots:
        parts.append("### Examples:")
        for ex in few_shots:
            parts.append(f"Q: {ex.question}\nSQL: {ex.sql}")
        parts.append("")
    if repair_hint is not None:
        bad_sql, error = repair_hint
        parts.append("### Previous attempt failed — fix it:")
        parts.append(f"Attempted SQL: {bad_sql}")
        parts.append(f"Error: {error}")
        parts.append("Write a corrected query.")
        parts.append("")
    parts.append(f"### Question:\n{question}\n\n### SQL:\n")
    return "\n".join(parts)
