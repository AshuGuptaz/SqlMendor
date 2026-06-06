"""API tests with a fake agent (no MLX) + a temp DB for the direct /sql path."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sqlmender.api.main import create_app
from sqlmender.config import get_settings


class FakeAgent:
    """Returns a canned grounded final state, mimicking agent.invoke."""

    def invoke(self, state):
        return {
            "question": state["question"],
            "status": "ok",
            "answer": "COUNT(*) = 220",
            "sql": "SELECT COUNT(*) FROM products",
            "result": {"columns": ["COUNT(*)"], "rows": [[220]], "row_count": 1, "error": None},
            "attempts": 1,
            "history": [
                {
                    "attempt": 1,
                    "sql": "SELECT COUNT(*) FROM products",
                    "error": None,
                    "verdict": "grounded",
                    "ok": True,
                }
            ],
        }


@pytest.fixture
def client(db_path, monkeypatch):
    import sqlmender.sql.executor as ex

    orig = ex.get_settings

    def _patched():
        s = orig()
        s.db_path = db_path
        return s

    monkeypatch.setattr(ex, "get_settings", _patched)
    app = create_app()
    app.state.agent = FakeAgent()
    return TestClient(app)


def _token(client):
    s = get_settings()
    r = client.post("/auth/token", data={"username": s.demo_username, "password": s.demo_password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_health_no_auth(client):
    assert client.get("/health").json()["status"] == "ok"


def test_schema_requires_jwt(client):
    assert client.get("/schema").status_code == 401


def test_schema_with_jwt(client):
    tok = _token(client)
    r = client.get("/schema", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and "products(" in r.json()["schema"]


def test_ask_requires_jwt(client):
    assert client.post("/ask", json={"question": "how many products?"}).status_code == 401


def test_ask_happy_path(client):
    tok = _token(client)
    r = client.post(
        "/ask", json={"question": "how many products?"}, headers={"Authorization": f"Bearer {tok}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["sql"].lower().startswith("select")
    assert body["row_count"] == 1 and len(body["history"]) == 1


def test_direct_sql_runs_with_jwt(client):
    tok = _token(client)
    r = client.post(
        "/sql",
        json={"question": "SELECT COUNT(*) FROM products"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200 and r.json()["row_count"] == 1


def test_direct_sql_rejects_mutation(client):
    tok = _token(client)
    r = client.post(
        "/sql", json={"question": "DROP TABLE products"}, headers={"Authorization": f"Bearer {tok}"}
    )
    assert r.status_code == 400
