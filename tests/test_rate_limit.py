import importlib
from typing import Any

from fastapi.testclient import TestClient


def reload_app_with_env(monkeypatch: Any, rate_limit_value: str, **extra: str) -> Any:
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", rate_limit_value)
    for k, v in extra.items():
        monkeypatch.setenv(k, v)
    import app.main as main

    importlib.reload(main)
    return main


def test_rate_limiting_blocks_after_limit(monkeypatch: Any) -> None:
    main = reload_app_with_env(monkeypatch, "2")
    client = TestClient(main.app)

    r1 = client.post("/api/calculate", json={"expression": "1+1"})
    r2 = client.post("/api/calculate", json={"expression": "2+2"})
    r3 = client.post("/api/calculate", json={"expression": "3+3"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429


def test_x_forwarded_for_ignored_by_default(monkeypatch: Any) -> None:
    main = reload_app_with_env(monkeypatch, "2")
    client = TestClient(main.app)

    headers_a = {"X-Forwarded-For": "1.1.1.1"}
    headers_b = {"X-Forwarded-For": "2.2.2.2"}
    # Both requests share the same TestClient host; XFF must NOT differentiate.
    r1 = client.post("/api/calculate", json={"expression": "1+1"}, headers=headers_a)
    r2 = client.post("/api/calculate", json={"expression": "1+1"}, headers=headers_b)
    r3 = client.post("/api/calculate", json={"expression": "1+1"}, headers=headers_a)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429


def test_x_forwarded_for_used_when_trusted(monkeypatch: Any) -> None:
    main = reload_app_with_env(monkeypatch, "2", RATE_LIMIT_TRUST_FORWARDED="1")
    client = TestClient(main.app)

    a = {"X-Forwarded-For": "1.1.1.1, 10.0.0.1"}
    b = {"X-Forwarded-For": "2.2.2.2"}
    # Two distinct client IPs — each should get its own bucket.
    assert client.post("/api/calculate", json={"expression": "1+1"}, headers=a).status_code == 200
    assert client.post("/api/calculate", json={"expression": "1+1"}, headers=a).status_code == 200
    assert client.post("/api/calculate", json={"expression": "1+1"}, headers=b).status_code == 200
    assert client.post("/api/calculate", json={"expression": "1+1"}, headers=b).status_code == 200
    # Third hit on 1.1.1.1 should be blocked while 2.2.2.2 still has room.
    assert client.post("/api/calculate", json={"expression": "1+1"}, headers=a).status_code == 429


def test_rate_store_evicts_oldest_when_at_capacity(monkeypatch: Any) -> None:
    main = reload_app_with_env(
        monkeypatch, "60", RATE_LIMIT_TRUST_FORWARDED="1", RATE_LIMIT_MAX_KEYS="2"
    )
    client = TestClient(main.app)

    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        client.post("/api/calculate", json={"expression": "1+1"}, headers={"X-Forwarded-For": ip})

    assert len(main._rate_store) == 2
    # 1.1.1.1 was the oldest entry and should have been evicted.
    assert "1.1.1.1" not in main._rate_store
    assert "3.3.3.3" in main._rate_store
