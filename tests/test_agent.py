"""The self-healing agent: happy / repair / abstain paths, driven by controllable
fake generators against the REAL executor + REAL execution-grounded critic."""

from __future__ import annotations

from sqlmender.agent.graph import build_agent
from sqlmender.agent.nodes import FALLBACK_ANSWER
from sqlmender.agent.state import initial_state
from sqlmender.config import get_settings
from sqlmender.llm.critic import critique
from sqlmender.sql.executor import execute_query


class _EmptyIndex:
    def retrieve(self, q, k=None):
        return []


def _agent(generator, db_path):
    s = get_settings()
    return build_agent(
        generator, critique, lambda sql: execute_query(sql, db_path), _EmptyIndex(), s
    )


def _run(agent):
    s = get_settings()
    return agent.invoke(initial_state("q", s.max_repair_attempts))


class Valid:
    name = "valid"

    def generate(self, q, few_shots=None, repair_hint=None):
        return "SELECT COUNT(*) FROM products"


class Flaky:
    """Wrong column first, correct on repair (reads the fed-back error)."""

    name = "flaky"

    def generate(self, q, few_shots=None, repair_hint=None):
        if repair_hint is not None:
            return "SELECT COUNT(*) FROM products"
        return "SELECT bogus_col FROM products"


class AlwaysBad:
    name = "bad"

    def generate(self, q, few_shots=None, repair_hint=None):
        return "SELECT * FROM nonexistent_table"


def test_happy_path_grounds_first_try(db_path):
    final = _run(_agent(Valid(), db_path))
    assert final["status"] == "ok"
    assert final["attempts"] == 1
    assert len(final["history"]) == 1 and final["history"][0]["ok"]


def test_repair_path_fixes_then_grounds(db_path):
    final = _run(_agent(Flaky(), db_path))
    assert final["status"] == "ok"
    assert final["attempts"] == 2
    assert final["history"][0]["ok"] is False  # first attempt errored
    assert "no such column" in (final["history"][0]["error"] or "")
    assert final["history"][1]["ok"] is True  # repair succeeded


def test_abstains_after_max_attempts(db_path):
    s = get_settings()
    final = _run(_agent(AlwaysBad(), db_path))
    assert final["status"] == "abstained"
    assert final["attempts"] == s.max_repair_attempts
    assert final["answer"] == FALLBACK_ANSWER


def test_history_records_every_attempt(db_path):
    final = _run(_agent(AlwaysBad(), db_path))
    assert len(final["history"]) == get_settings().max_repair_attempts
