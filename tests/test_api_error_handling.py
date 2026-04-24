from fastapi.testclient import TestClient

from app.main import app


def test_api_unexpected_error(monkeypatch):
    def raise_err(expr):
        raise RuntimeError("boom")

    # Patch the function used by app.main (safe_eval was imported there at module import time)
    monkeypatch.setattr("app.main.safe_eval", raise_err)
    with TestClient(app) as client:
        res = client.post("/api/calculate", json={"expression": "1+1"})
        assert res.status_code == 500
        data = res.json()
        assert "error" in data and "システムエラーが発生しました" in data["error"]


def test_html_unexpected_error(monkeypatch):
    def raise_err(expr):
        raise RuntimeError("boom")

    # Patch the function used by app.main
    monkeypatch.setattr("app.main.safe_eval", raise_err)
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    res = client.post("/calculate", data={"expression": "1+1"})
    assert res.status_code == 500
