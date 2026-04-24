import asyncio

from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from app.main import app, rate_limit_middleware


def test_rate_limit_middleware_client_missing():
    # Build a minimal ASGI scope without 'client' to simulate request.client being falsy
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/test-mw",
        "headers": [],
    }
    req = Request(scope)

    async def next_fn(request):
        return Response("ok")

    # Run the middleware directly
    resp = asyncio.run(rate_limit_middleware(req, next_fn))
    assert isinstance(resp, Response)
    assert resp.status_code == 200


def test_show_fraction_non_numeric(monkeypatch):
    # Make safe_eval return a non-numeric value while show_fraction is True
    monkeypatch.setattr("app.services.calculator.safe_eval", lambda expr: "non-numeric")
    # app.main imported safe_eval at module import time; patch that reference too
    monkeypatch.setattr("app.main.safe_eval", lambda expr: "non-numeric")

    with TestClient(app) as client:
        # HTML form
        res = client.post("/calculate", data={"expression": "ignored", "show_fraction": "on"})
        assert res.status_code == 200
        assert "non-numeric" in res.text

        # API
        res = client.post("/api/calculate", json={"expression": "ignored", "show_fraction": True})
        assert res.status_code == 200
        assert res.json().get("result") == "non-numeric"
