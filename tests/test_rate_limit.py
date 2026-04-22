import importlib
import time

import pytest
from fastapi.testclient import TestClient


def reload_app_with_env(monkeypatch, rate_limit_value: str):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", rate_limit_value)
    import app.main as main
    importlib.reload(main)
    return main.app


def test_rate_limiting_blocks_after_limit(monkeypatch):
    app = reload_app_with_env(monkeypatch, "2")
    client = TestClient(app)

    # two allowed requests
    r1 = client.post("/api/calculate", json={"expression": "1+1"})
    r2 = client.post("/api/calculate", json={"expression": "2+2"})
    r3 = client.post("/api/calculate", json={"expression": "3+3"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
