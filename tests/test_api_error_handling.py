from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def test_api_unexpected_error(monkeypatch: Any) -> None:
    def raise_err(expr: Any) -> Any:
        raise RuntimeError("boom")

    # Patch the calculator instance used by app.main
    monkeypatch.setattr("app.main.calc.safe_eval", raise_err)
    with TestClient(app) as client:
        res = client.post("/api/calculate", json={"expression": "1+1"})
        assert res.status_code == 500
        data = res.json()
        assert "error" in data and "システムエラーが発生しました" in data["error"]


def test_html_unexpected_error(monkeypatch: Any) -> None:
    def raise_err(expr: Any) -> Any:
        raise RuntimeError("boom")

    # Patch the instance used by app.main
    monkeypatch.setattr("app.main.calc.safe_eval", raise_err)
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    res = client.post("/calculate", data={"expression": "1+1"})
    assert res.status_code == 500
