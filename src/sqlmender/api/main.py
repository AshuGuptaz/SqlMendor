"""FastAPI app factory.

Builds the self-healing agent on startup and attaches it to ``app.state.agent``.
The agent uses the fine-tuned MLX model when it's available (Apple Silicon + a
trained adapter) and otherwise the deterministic heuristic generator — so ``/ask``
works in every environment, with the model being a drop-in upgrade."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from sqlmender.api.routes import router
from sqlmender.config import get_settings

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title="SQLMender API", version="1.0.0")
    app.include_router(router)
    try:
        from sqlmender.agent.graph import build_default_agent
        from sqlmender.llm.generator import get_generator, mlx_available

        settings = get_settings()
        app.state.agent = build_default_agent(settings)
        gen = get_generator(settings)
        logger.info("Agent ready (generator: {}).", gen.name)
    except Exception as e:  # noqa: BLE001
        app.state.agent = None
        logger.warning("Agent unavailable: {}", e)
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")
    return app


app = create_app()
