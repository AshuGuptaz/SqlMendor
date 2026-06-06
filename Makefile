# SQLMender — self-correcting, fine-tuned NL->SQL agent
PY ?= python3.11
VENV := .venv
BIN := $(VENV)/bin
export PYTHONPATH := src

.PHONY: help install data train eval test lint fmt dev clean
help:
	@echo "install  create venv + install (editable, with dev extras)"
	@echo "data     build the SQLite DB, generate the dataset, prep MLX files"
	@echo "train    fine-tune the LoRA adapter (Apple Silicon / MLX)"
	@echo "eval     run the agent over the test set -> outputs/eval.json"
	@echo "test     pytest (excludes MLX 'integration' tests)"
	@echo "lint     ruff + black --check    |  fmt: autoformat"
	@echo "dev      serve API + dashboard at http://localhost:8000"

install:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

data:
	$(BIN)/python -m sqlmender.db.build_db
	$(BIN)/python -m sqlmender.train.data_gen
	$(BIN)/python -m sqlmender.train.prepare_mlx

train:
	$(BIN)/python -m sqlmender.train.train

eval:
	$(BIN)/python scripts/run_eval.py

test:
	$(BIN)/pytest -q --cov=sqlmender --cov-report=term-missing

lint:
	$(BIN)/ruff check src tests scripts
	$(BIN)/black --check src tests scripts

fmt:
	$(BIN)/ruff check --fix src tests scripts
	$(BIN)/black src tests scripts

dev:
	$(BIN)/uvicorn sqlmender.api.main:app --reload --port 8000

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache **/__pycache__ .coverage
