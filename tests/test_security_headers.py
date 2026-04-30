import importlib
from typing import Any

from fastapi.testclient import TestClient


def reload_app(monkeypatch: Any, **env: str) -> Any:
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app.main as main

    importlib.reload(main)
    return main


def test_default_security_headers_present(monkeypatch: Any) -> None:
    main = reload_app(monkeypatch)
    client = TestClient(main.app)
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("x-frame-options") == "DENY"
    csp = res.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_hsts_emitted_only_over_https(monkeypatch: Any) -> None:
    main = reload_app(monkeypatch)
    client = TestClient(main.app)
    plain = client.get("/")
    assert "strict-transport-security" not in {k.lower() for k in plain.headers.keys()}

    forwarded = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert forwarded.headers.get("strict-transport-security", "").startswith("max-age=")


def test_security_headers_disabled_by_env(monkeypatch: Any) -> None:
    main = reload_app(monkeypatch, SECURITY_HEADERS_ENABLED="0")
    client = TestClient(main.app)
    res = client.get("/")
    assert res.status_code == 200
    assert "x-content-type-options" not in {k.lower() for k in res.headers.keys()}
    assert "content-security-policy" not in {k.lower() for k in res.headers.keys()}


def test_security_headers_applied_to_rate_limit_response(monkeypatch: Any) -> None:
    main = reload_app(monkeypatch, RATE_LIMIT_PER_MIN="1")
    client = TestClient(main.app)
    client.post("/api/calculate", json={"expression": "1+1"})
    res = client.post("/api/calculate", json={"expression": "1+1"})
    assert res.status_code == 429
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert "default-src 'self'" in res.headers.get("content-security-policy", "")


def test_csp_can_be_overridden(monkeypatch: Any) -> None:
    main = reload_app(monkeypatch, CSP_POLICY="default-src 'none'")
    client = TestClient(main.app)
    res = client.get("/")
    assert res.headers.get("content-security-policy") == "default-src 'none'"
