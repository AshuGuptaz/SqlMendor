from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlmender.db.build_db import build  # noqa: E402


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> str:
    return build(str(tmp_path_factory.mktemp("db") / "test.db"), seed=7)
