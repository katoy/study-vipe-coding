import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def calc(client, expr):
    res = client.post("/api/calculate", json={"expression": expr})
    # FastAPI returns HTML; we parse JSON if possible, else fallback to text
    try:
        return res.json(), res.status_code
    except Exception:
        return {"error": res.text}, res.status_code


def test_page_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "計算機" in res.text


def test_addition(client):
    data, code = calc(client, "3 + 5")
    assert code == 200
    assert data.get("result") == 8


def test_subtraction(client):
    data, code = calc(client, "9 - 4")
    assert code == 200
    assert data.get("result") == 5


def test_multiplication(client):
    data, code = calc(client, "7 * 3")
    assert code == 200
    assert data.get("result") == 21


def test_division(client):
    data, code = calc(client, "10 / 2")
    assert code == 200
    assert data.get("result") == 5


def test_division_by_zero(client):
    data, code = calc(client, "5 / 0")
    assert code == 400
    assert "0で割ること" in data.get("error", "")


def test_decimal(client):
    data, code = calc(client, "1.5 + 1.5")
    assert code == 200
    assert data.get("result") == 3


def test_percent(client):
    data, code = calc(client, "10 % 3")
    assert code == 200
    assert data.get("result") == 1


def test_chained(client):
    data, _ = calc(client, "10 / 2")
    assert data.get("result") == 5
    data, _ = calc(client, f"{data.get('result')} * 3")
    assert data.get("result") == 15


def test_invalid_expression(client):
    data, code = calc(client, "abc + def")
    assert code == 400
    assert "error" in data


def test_large_numbers(client):
    data, code = calc(client, "999999 * 999999")
    assert code == 200
    assert data.get("result") == 999999 * 999999


def test_modulo_by_zero(client):
    data, code = calc(client, "5 % 0")
    assert code == 400
    assert "0で割ること" in data.get("error", "")


def test_negative_number(client):
    data, code = calc(client, "-5 + 3")
    assert code == 200
    assert data.get("result") == -2


def test_positive_number(client):
    data, code = calc(client, "+5 + 3")
    assert code == 200
    assert data.get("result") == 8


def test_expression_too_long(client):
    data, code = calc(client, "1" * 101)
    assert code == 400
    assert "error" in data


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('id')",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd').read()",
        "[].__class__.__mro__[-1].__subclasses__()",
    ],
)
def test_injection_blocked(client, expr):
    data, code = calc(client, expr)
    assert code == 400
    assert "error" in data


# Additional HTML endpoint tests for full coverage


def test_calculate_html_success(client):
    res = client.post("/calculate", data={"expression": "2+3"})
    assert res.status_code == 200
    # The result should be present in the returned HTML
    assert "5" in res.text


def test_calculate_html_divide_by_zero(client):
    res = client.post("/calculate", data={"expression": "5/0"})
    assert res.status_code == 200
    assert "0で割ることはできません" in res.text


def test_calculate_html_invalid_expression(client):
    res = client.post("/calculate", data={"expression": "abc+def"})
    assert res.status_code == 200
    assert "計算式が正しくありません" in res.text
