import importlib
from typing import Any

from fastapi.testclient import TestClient


def reload_app_with_env(monkeypatch: Any, allow_origins_value: str) -> Any:
    """Set ALLOW_ORIGINS env and reload app.main, returning the app object."""
    monkeypatch.setenv("ALLOW_ORIGINS", allow_origins_value)
    import app.main as main

    importlib.reload(main)
    return main.app


def test_cors_allows_configured_origin(monkeypatch: Any) -> None:
    app = reload_app_with_env(monkeypatch, "https://allowed.example")
    client = TestClient(app)
    res = client.get("/", headers={"Origin": "https://allowed.example"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://allowed.example"


def test_cors_blocks_other_origin(monkeypatch: Any) -> None:
    app = reload_app_with_env(monkeypatch, "https://allowed.example")
    client = TestClient(app)
    res = client.get("/", headers={"Origin": "https://forbidden.example"})
    # If origin is not allowed, Access-Control-Allow-Origin should not echo the forbidden origin
    assert res.headers.get("access-control-allow-origin") != "https://forbidden.example"
