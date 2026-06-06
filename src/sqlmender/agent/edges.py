"""Conditional routing after the critic node — a pure function of state."""

from __future__ import annotations

from sqlmender.agent.state import AgentState


def route_after_critic(state: AgentState) -> str:
    """END if grounded; loop back to GENERATE to repair while attempts remain;
    otherwise ABSTAIN."""
    if state.get("status") == "ok":
        return "done"
    if state.get("attempts", 0) < state.get("max_attempts", 3):
        return "repair"
    return "abstain"
