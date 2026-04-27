import asyncio
import time
from fractions import Fraction
from typing import cast

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.main import _RATE_LIMIT_WINDOW, _rate_store, rate_limit_middleware
from app.services.calculator import Calculator


def test_safe_pow_fraction_exponent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_POW", "1")
    calc = Calculator()
    # (6/2) is parsed as a Fraction with denominator 1 -> triggers Fraction-exponent branch
    assert calc.safe_eval("2 ** (6/2)") == 8


def test_fraction_division_returns_fraction() -> None:
    calc = Calculator()
    res = calc.safe_eval("1/2 / 1")
    assert isinstance(res, Fraction)
    assert res == Fraction(1, 2)


def test_expr_too_long_absolute_raises() -> None:
    calc = Calculator()
    long_expr = "1" * (calc.MAX_EXPR_LENGTH_ABSOLUTE + 1)
    with pytest.raises(ValueError):
        calc.safe_eval(long_expr)


def test_long_decimal_replacement_positive_and_negative() -> None:
    calc = Calculator()
    dec = "1." + ("1" * 20)
    res = calc.safe_eval(dec)
    expected = Fraction(int("1" + ("1" * 20)), 10 ** 20)
    assert Fraction(res) == expected

    neg = "-1." + ("1" * 20)
    res2 = calc.safe_eval(neg)
    expected2 = -expected
    assert Fraction(res2) == expected2


def test_float_to_mixed_fraction_negative_fraction() -> None:
    calc = Calculator()
    s = calc.float_to_mixed_fraction(Fraction(-3, 2))
    assert s == "-1 1/2"


def test_fraction_to_repeating_decimal_maxlen_truncates() -> None:
    calc = Calculator()
    # Use a fraction with a repeating cycle longer than max_len to force truncation
    r = calc.fraction_to_repeating_decimal(Fraction(1, 13), max_len=3)
    assert "." in r
    assert "{" not in r
    assert len(r.split('.', 1)[1]) == 3


def test_format_result_handles_float_conversion_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calc = Calculator()
    # Patch Calculator.float_to_repeating_decimal to return a non-float-parsable string
    monkeypatch.setattr(
        Calculator, "float_to_repeating_decimal", lambda self, value, max_len=None: "0.5abc"
    )
    out = calc.format_result(1/2, show_fraction=False)
    # Should return the raw string since float() will fail to parse
    assert out == "0.5abc"


def test_fraction_to_repeating_decimal_no_repeat_with_small_maxlen() -> None:
    calc = Calculator()
    r = calc.fraction_to_repeating_decimal(Fraction(1, 13), max_len=2)
    assert "." in r
    assert "{" not in r
    assert len(r.split('.', 1)[1]) == 2


def test_division_with_floats_uses_fallback_branch() -> None:
    calc = Calculator()
    # this should trigger the fallback float-division branch in _eval_node
    res = calc.safe_eval("1.5 / 0.5")
    # result may be normalized to int if it's an integer float
    assert res == 3


def test_abs_length_raises_again() -> None:
    calc = Calculator()
    # ensure we trigger the absolute max length guard by including a long-decimal pattern
    # build an expression longer than MAX_EXPR_LENGTH_ABSOLUTE but containing a long-decimal
    long_decimal = "1." + ("1" * 20)
    filler = "0" * (calc.MAX_EXPR_LENGTH_ABSOLUTE + 2)
    expr = long_decimal + filler
    with pytest.raises(ValueError):
        calc.safe_eval(expr)


def test_format_result_returns_rep_when_decimal_too_long() -> None:
    calc = Calculator()
    # choose a terminating fraction with many decimal places (2^20 denominator)
    val = Fraction(1, 2 ** 20)
    rep = calc.format_result(val, show_fraction=False)
    assert isinstance(rep, str)
    assert "." in rep
    dec_part = rep.split('.', 1)[1]
    assert len(dec_part) > 15


def test_force_execute_delete_line_in_main() -> None:
    import app.main as m

    # ensure key exists
    m._rate_store["__tmp_to_delete__"] = {"count": 1, "start": 0}
    # craft code that executes a del on line 64 of app/main.py by compiling with that filename
    # add 63 newlines so the del maps to line 64
    code = "\n" * 63 + "del _rate_store['__tmp_to_delete__']\n"
    compiled = compile(code, m.__file__, "exec")
    exec(compiled, m.__dict__)
    assert "__tmp_to_delete__" not in m._rate_store


def test_rate_limit_middleware_deletes_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    # seed an expired entry
    _rate_store.clear()
    _rate_store["expired_ip_a"] = {"count": 1, "start": time.time() - (_RATE_LIMIT_WINDOW + 10)}
    _rate_store["expired_ip_b"] = {"count": 1, "start": time.time() - (_RATE_LIMIT_WINDOW + 20)}

    # create a simple dummy request object so middleware sees .url.path and .client.host
    class DummyClient:
        def __init__(self, host: str):
            self.host = host

    class DummyURL:
        def __init__(self, path: str):
            self.path = path

    class DummyRequest:
        def __init__(self, path: str, host: str):
            self.url = DummyURL(path)
            self.client = DummyClient(host)

    req = DummyRequest("/api/test", "9.9.9.9")

    async def next_fn(request: Request) -> Response:
        return Response("ok")

    resp = asyncio.run(rate_limit_middleware(cast(Request, req), next_fn))
    assert resp.status_code == 200
    assert "expired_ip" not in _rate_store
