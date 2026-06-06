"""Assemble the self-healing SQL agent as a cyclical LangGraph.

    START -> retrieve -> generate -> execute -> critic
                              ^                     |
                              |     (repair)        v
                              +----------------- route ----> abstain -> END
                                                   |
                                                   +--------> END (grounded)

Dependencies (generator, critic, executor, example index) are injected so the same
graph runs with the fine-tuned model in production and with fakes in tests.
"""

from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from sqlmender.agent.edges import route_after_critic
from sqlmender.agent.nodes import (
    abstain_node,
    make_critic_node,
    make_execute_node,
    make_generate_node,
    make_retrieve_node,
)
from sqlmender.agent.state import AgentState, initial_state
from sqlmender.config import Settings, get_settings
from sqlmender.llm.critic import Verdict
from sqlmender.sql.executor import QueryResult


def build_agent(
    generator, critic, executor: Callable[[str], QueryResult], example_index, settings: Settings
):
    g = StateGraph(AgentState)
    g.add_node("retrieve", make_retrieve_node(example_index, settings))
    g.add_node("generate", make_generate_node(generator))
    g.add_node("execute", make_execute_node(executor))
    g.add_node("critic", make_critic_node(critic, settings))
    g.add_node("abstain", abstain_node)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "execute")
    g.add_edge("execute", "critic")
    g.add_conditional_edges(
        "critic", route_after_critic, {"done": END, "repair": "generate", "abstain": "abstain"}
    )
    g.add_edge("abstain", END)
    return g.compile()


def build_default_agent(settings: Settings | None = None):
    """Wire the real backends: heuristic-or-MLX generator, execution-grounded critic,
    safe executor, BM25 few-shot index."""
    s = settings or get_settings()
    from sqlmender.llm.critic import critique
    from sqlmender.llm.generator import get_generator
    from sqlmender.retrieval.example_index import ExampleIndex
    from sqlmender.sql.executor import execute_query

    def executor(sql: str) -> QueryResult:
        return execute_query(sql, s.db_path)

    return build_agent(
        generator=get_generator(s),
        critic=critique,
        executor=executor,
        example_index=ExampleIndex.from_jsonl(s.train_data_path),
        settings=s,
    )


def ask(question: str, settings: Settings | None = None) -> AgentState:
    s = settings or get_settings()
    agent = build_default_agent(s)
    return agent.invoke(initial_state(question, s.max_repair_attempts))


__all__ = ["build_agent", "build_default_agent", "ask", "Verdict"]
