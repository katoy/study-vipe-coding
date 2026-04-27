from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Any:
    with TestClient(app) as c:
        yield c


def calc(client: Any, expr: Any) -> Any:
    res = client.post("/api/calculate", json={"expression": expr})
    # FastAPI returns HTML; we parse JSON if possible, else fallback to text
    try:
        return res.json(), res.status_code
    except Exception:
        return {"error": res.text}, res.status_code


def test_page_loads(client: Any) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "計算機" in res.text


def test_addition(client: Any) -> None:
    data, code = calc(client, "3 + 5")
    assert code == 200
    assert data.get("result") == 8


def test_subtraction(client: Any) -> None:
    data, code = calc(client, "9 - 4")
    assert code == 200
    assert data.get("result") == 5


def test_multiplication(client: Any) -> None:
    data, code = calc(client, "7 * 3")
    assert code == 200
    assert data.get("result") == 21


def test_division(client: Any) -> None:
    data, code = calc(client, "10 / 2")
    assert code == 200
    assert data.get("result") == 5


def test_division_by_zero(client: Any) -> None:
    data, code = calc(client, "5 / 0")
    assert code == 400
    assert "0で割ること" in data.get("error", "")


def test_decimal(client: Any) -> None:
    data, code = calc(client, "1.5 + 1.5")
    assert code == 200
    assert data.get("result") == 3


def test_percent(client: Any) -> None:
    data, code = calc(client, "10 % 3")
    assert code == 200
    assert data.get("result") == 1


def test_chained(client: Any) -> None:
    data, _ = calc(client, "10 / 2")
    assert data.get("result") == 5
    data, _ = calc(client, f"{data.get('result')} * 3")
    assert data.get("result") == 15


def test_invalid_expression(client: Any) -> None:
    data, code = calc(client, "abc + def")
    assert code == 400
    assert "error" in data


def test_large_numbers(client: Any) -> None:
    data, code = calc(client, "999999 * 999999")
    assert code == 200
    assert data.get("result") == 999999 * 999999


def test_modulo_by_zero(client: Any) -> None:
    data, code = calc(client, "5 % 0")
    assert code == 400
    assert "0で割ること" in data.get("error", "")


def test_negative_number(client: Any) -> None:
    data, code = calc(client, "-5 + 3")
    assert code == 200
    assert data.get("result") == -2


def test_positive_number(client: Any) -> None:
    data, code = calc(client, "+5 + 3")
    assert code == 200
    assert data.get("result") == 8


def test_expression_too_long(client: Any) -> None:
    data, code = calc(client, "1" * 101)
    assert code == 400
    assert "error" in data


def test_deep_nesting(client: Any) -> None:
    # Create expression with deep parentheses to trigger depth guard
    depth = 70
    expr = "(" * depth + "1" + ")" * depth
    data, code = calc(client, expr)
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
def test_injection_blocked(client: Any, expr: Any) -> None:
    data, code = calc(client, expr)
    assert code == 400
    assert "error" in data


# Additional HTML endpoint tests for full coverage


def test_calculate_html_success(client: Any) -> None:
    res = client.post("/calculate", data={"expression": "2+3"})
    assert res.status_code == 200
    # The result should be present in the returned HTML
    assert "5" in res.text


def test_calculate_html_divide_by_zero(client: Any) -> None:
    res = client.post("/calculate", data={"expression": "5/0"})
    assert res.status_code == 200
    assert "0で割ることはできません" in res.text


def test_calculate_html_invalid_expression(client: Any) -> None:
    res = client.post("/calculate", data={"expression": "abc+def"})
    assert res.status_code == 200
    assert "計算式が正しくありません" in res.text


def test_calculate_html_show_fraction(client: Any) -> None:
    # POST form with show_fraction checkbox present
    res = client.post("/calculate", data={"expression": "3/2", "show_fraction": "on"})
    assert res.status_code == 200
    assert "1 1/2" in res.text


def test_api_show_fraction(client: Any) -> None:
    data, code = calc(client, "3/2")
    # default: no fraction
    assert code == 200
    assert data.get("result") == 1.5

    # request fraction formatting via API
    res = client.post("/api/calculate", json={"expression": "3/2", "show_fraction": True})
    assert res.status_code == 200
    j = res.json()
    assert j.get("result") == "1 1/2"


def test_api_repeating_decimal_default(client: Any) -> None:
    # 1/3 should be represented as repeating decimal by default
    data, code = calc(client, "1/3")
    assert code == 200
    assert data.get("result") == "0.{3}"


def test_calculate_html_repeating_decimal(client: Any) -> None:
    res = client.post("/calculate", data={"expression": "1/3"})
    assert res.status_code == 200
    assert "0.{3}" in res.text


def test_calculate_html_terminating_decimal(client: Any) -> None:
    res = client.post("/calculate", data={"expression": "1/2"})
    assert res.status_code == 200
    assert "0.5" in res.text


def test_repeating_decimal_input_evaluation(client: Any) -> None:
    # UI may send expressions like "0.(3)*9" — ensure server accepts and evaluates
    data, code = calc(client, "0.{3}*9")
    assert code == 200
    assert data.get("result") == 3
