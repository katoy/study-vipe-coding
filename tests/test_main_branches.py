import asyncio

from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from app.main import app, rate_limit_middleware


def test_rate_limit_middleware_client_missing():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/test-mw",
        "headers": [],
    }
    req = Request(scope)

    async def next_fn(request):
        return Response("ok")

    resp = asyncio.run(rate_limit_middleware(req, next_fn))
    assert isinstance(resp, Response)
    assert resp.status_code == 200


def test_show_fraction_non_numeric(monkeypatch):
    # Make Calculator.safe_eval return a non-numeric value while show_fraction is True
    monkeypatch.setattr("app.services.calculator.Calculator.safe_eval", lambda self, expr: "non-numeric")
    # patch the instance used by app.main
    monkeypatch.setattr("app.main.calc.safe_eval", lambda expr: "non-numeric")

    with TestClient(app) as client:
        res = client.post("/calculate", data={"expression": "ignored", "show_fraction": "on"})
        assert res.status_code == 200
        assert "non-numeric" in res.text

        res = client.post("/api/calculate", json={"expression": "ignored", "show_fraction": True})
        assert res.status_code == 200
        assert res.json().get("result") == "non-numeric"
