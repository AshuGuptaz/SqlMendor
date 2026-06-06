"""Configuration for SQLMender — a self-correcting, fine-tuned NL->SQL agent."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = str(ROOT / "data" / "ecommerce.db")
    base_model: str = "mlx-community/Qwen2.5-3B-Instruct-4bit"
    adapter_path: str = str(ROOT / "adapters" / "sql-lora")

    # LoRA hyperparameters (per spec)
    lora_rank: int = 16
    learning_rate: float = 1e-5
    iters: int = 600
    batch_size: int = 1

    # executor
    query_timeout_seconds: float = 5.0
    max_rows: int = 1000

    # self-healing agent
    max_repair_attempts: int = 3  # total generate attempts before abstaining
    repair_on_empty_result: bool = True  # treat a 0-row answer as a (soft) repair signal

    # retrieval (few-shot examples injected into the prompt)
    few_shot_k: int = 3
    train_data_path: str = str(ROOT / "data" / "train.jsonl")

    # groq
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    # auth
    jwt_secret: str = Field(default="dev-secret-change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    demo_username: str = Field(default="demo", alias="DEMO_USERNAME")
    demo_password: str = Field(default="demo-password", alias="DEMO_PASSWORD")


def get_settings() -> Settings:
    return Settings()
