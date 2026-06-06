"""Graph nodes, built as factories so the generator, critic, executor and example
index can be injected (real backends in production, fakes in tests)."""

from __future__ import annotations

from collections.abc import Callable

from sqlmender.agent.state import AgentState
from sqlmender.config import Settings
from sqlmender.llm.critic import Verdict
from sqlmender.schemas import SQLExample
from sqlmender.sql.executor import QueryResult, UnsafeQueryError

FALLBACK_ANSWER = (
    "I couldn't produce a query that runs correctly against the database after "
    "several attempts, so I'm not going to guess. Try rephrasing the question."
)


def make_retrieve_node(example_index, settings: Settings) -> Callable[[AgentState], dict]:
    def retrieve(state: AgentState) -> dict:
        shots: list[SQLExample] = example_index.retrieve(state["question"], settings.few_shot_k)
        return {"few_shots": [s.model_dump() for s in shots]}

    return retrieve


def make_generate_node(generator) -> Callable[[AgentState], dict]:
    def generate(state: AgentState) -> dict:
        shots = [SQLExample(**s) for s in state.get("few_shots", [])]
        sql = generator.generate(
            state["question"], few_shots=shots, repair_hint=state.get("repair_hint")
        )
        return {"sql": sql, "attempts": state.get("attempts", 0) + 1}

    return generate


def make_execute_node(executor: Callable[[str], QueryResult]) -> Callable[[AgentState], dict]:
    def execute(state: AgentState) -> dict:
        try:
            res = executor(state["sql"])
        except UnsafeQueryError as e:
            res = QueryResult(error=str(e))
        return {
            "result": {
                "columns": res.columns,
                "rows": res.rows,
                "row_count": res.row_count,
                "error": res.error,
            }
        }

    return execute


def make_critic_node(
    critic: Callable[..., Verdict], settings: Settings
) -> Callable[[AgentState], dict]:
    def critic_node(state: AgentState) -> dict:
        r = state["result"]
        result = QueryResult(columns=r["columns"], rows=r["rows"], error=r["error"])
        verdict = critic(state["question"], state["sql"], result, state["attempts"], settings)
        history = list(state.get("history", []))
        history.append(
            {
                "attempt": state["attempts"],
                "sql": state["sql"],
                "error": r["error"],
                "verdict": verdict.reason,
                "ok": verdict.ok,
            }
        )
        out: dict = {"history": history}
        if verdict.ok:
            out["status"] = "ok"
            out["answer"] = _summarize(state["question"], result)
            out["repair_hint"] = None
        else:
            out["repair_hint"] = verdict.hint
        return out

    return critic_node


def abstain_node(state: AgentState) -> dict:
    return {"status": "abstained", "answer": FALLBACK_ANSWER}


def _summarize(question: str, result: QueryResult) -> str:
    if result.row_count == 1 and len(result.columns) == 1:
        return f"{result.columns[0]} = {result.rows[0][0]}"
    return f"Returned {result.row_count} row(s) across columns: {', '.join(result.columns)}."
