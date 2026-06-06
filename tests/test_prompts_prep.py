from __future__ import annotations

import json

from sqlmender.llm.prompts import build_agent_prompt
from sqlmender.schemas import SQLExample
from sqlmender.train.prepare_mlx import convert
from sqlmender.train.prompt import build_prompt


def test_training_prompt_has_schema_and_marker():
    p = build_prompt("How many products are there?")
    assert "customers(" in p and p.rstrip().endswith("### SQL:")


def test_agent_prompt_injects_fewshots_and_repair():
    shots = [SQLExample(question="count products", sql="SELECT COUNT(*) FROM products")]
    p = build_agent_prompt(
        "how many products?", few_shots=shots, repair_hint=("SELECT bad", "no such column: bad")
    )
    assert "### Examples:" in p and "count products" in p
    assert "Previous attempt failed" in p and "no such column: bad" in p
    assert p.rstrip().endswith("### SQL:")


def test_agent_prompt_minimal():
    p = build_agent_prompt("how many products?")
    assert "### Examples:" not in p and "Previous attempt" not in p


def test_prepare_mlx_convert(tmp_path):
    src = tmp_path / "train.jsonl"
    src.write_text(
        json.dumps({"question": "count products", "sql": "SELECT COUNT(*) FROM products"}) + "\n"
    )
    dst = tmp_path / "mlx" / "train.jsonl"
    assert convert(src, dst) == 1
    rec = json.loads(dst.read_text().splitlines()[0])
    assert set(rec) == {"prompt", "completion"} and rec["completion"].strip().startswith("SELECT")
