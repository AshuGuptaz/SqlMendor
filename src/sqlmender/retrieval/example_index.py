"""Few-shot retrieval: given a question, fetch the most similar (question, SQL)
pairs from the training set to use as in-context demonstrations.

Uses BM25 over the training questions — light, deterministic, and effective for
this schema. This is the retrieval-augmented half of the agent: relevant examples
are injected into the prompt so the model sees the project's exact SQL style."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from sqlmender.config import get_settings
from sqlmender.schemas import SQLExample

_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class ExampleIndex:
    """BM25 index over training questions for few-shot retrieval."""

    def __init__(self, examples: list[SQLExample]):
        self.examples = examples
        self._bm25 = BM25Okapi([_tok(e.question) for e in examples]) if examples else None

    @classmethod
    def from_jsonl(cls, path: str | None = None) -> ExampleIndex:
        path = path or get_settings().train_data_path
        p = Path(path)
        if not p.exists():
            return cls([])
        rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        return cls([SQLExample(**r) for r in rows])

    def retrieve(self, question: str, k: int | None = None) -> list[SQLExample]:
        k = k if k is not None else get_settings().few_shot_k
        if not self._bm25 or not self.examples:
            return []
        scores = self._bm25.get_scores(_tok(question))
        ranked = sorted(range(len(self.examples)), key=lambda i: scores[i], reverse=True)
        return [self.examples[i] for i in ranked[:k]]
