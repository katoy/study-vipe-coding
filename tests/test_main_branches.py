import asyncio
from starlette.requests import Request
from starlette.responses import Response

import pytest

from app.main import rate_limit_middleware


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
        return Response('ok')

    # Run the middleware directly
    resp = asyncio.get_event_loop().run_until_complete(rate_limit_middleware(req, next_fn))
    assert isinstance(resp, Response)
    assert resp.status_code == 200


def test_show_fraction_non_numeric(monkeypatch, client):
    # Make safe_eval return a non-numeric value while show_fraction is True
    monkeypatch.setattr("app.services.calculator.safe_eval", lambda expr: "non-numeric")

    # HTML form
    res = client.post("/calculate", data={"expression": "ignored", "show_fraction": "on"})
    assert res.status_code == 200
    assert "non-numeric" in res.text

    # API
    res = client.post("/api/calculate", json={"expression": "ignored", "show_fraction": True})
    assert res.status_code == 200
    assert res.json().get("result") == "non-numeric"
