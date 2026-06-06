"""Fine-tune the 4-bit Qwen with MLX LoRA on the text-to-SQL data.

Hyperparameters (per spec): rank=16, lr=1e-5, iters=600, batch_size=1, grad
checkpointing. Drives ``mlx_lm.lora`` via a YAML config; parses loss into
``outputs/training_log.jsonl``.

Requires Apple Silicon (MLX). On an M1/16GB the 4-bit base + rank-16 adapter fits;
expect this to be slower than an M4 — budget accordingly for 600 iters.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from loguru import logger

from sqlmender.config import get_settings

ROOT = Path(__file__).resolve().parents[3]
MLX_DIR = Path(get_settings().db_path).resolve().parent / "mlx"
LOG_PATH = ROOT / "outputs" / "training_log.jsonl"
_TRAIN_RE = re.compile(r"Iter (\d+): Train loss ([\d.]+)")
_VAL_RE = re.compile(r"Iter (\d+): Val loss ([\d.]+)")


def _require_mlx() -> None:
    try:
        import mlx_lm  # noqa: F401
    except Exception as e:  # noqa: BLE001
        logger.error("MLX unavailable: {}. Training requires an Apple Silicon Mac.", e)
        sys.exit(1)


def main() -> None:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=s.base_model)
    ap.add_argument("--iters", type=int, default=s.iters)
    ap.add_argument("--rank", type=int, default=s.lora_rank)
    ap.add_argument("--lr", type=float, default=s.learning_rate)
    ap.add_argument("--batch-size", type=int, default=s.batch_size)
    args = ap.parse_args()

    _require_mlx()
    adapter_dir = Path(s.adapter_path)
    adapter_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "model": args.model,
        "train": True,
        "data": str(MLX_DIR),
        "adapter_path": str(adapter_dir),
        "iters": args.iters,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "steps_per_report": 20,
        "steps_per_eval": 100,
        "val_batches": 20,
        "save_every": 200,
        "max_seq_length": 1024,
        "grad_checkpoint": True,
        "lora_parameters": {
            "rank": args.rank,
            "alpha": args.rank * 2,
            "dropout": 0.0,
            "scale": 10.0,
        },
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
        cfg_path = Path(tmp.name)
    cfg_path.write_text(yaml.safe_dump(cfg))
    logger.info("LoRA config -> {}", cfg_path)

    cmd = [sys.executable, "-m", "mlx_lm.lora", "--config", str(cfg_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        logger.error("mlx_lm.lora exited {}", proc.returncode)
        sys.exit(proc.returncode)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for line in (proc.stdout + proc.stderr).splitlines():
        if m := _TRAIN_RE.search(line):
            entries.append({"iter": int(m.group(1)), "split": "train", "loss": float(m.group(2))})
        elif m := _VAL_RE.search(line):
            entries.append({"iter": int(m.group(1)), "split": "valid", "loss": float(m.group(2))})
    with LOG_PATH.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    logger.success("Adapter -> {} ; {} loss entries -> {}", adapter_dir, len(entries), LOG_PATH)


if __name__ == "__main__":
    main()
