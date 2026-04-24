import pytest
from app.services.calculator import safe_eval, float_to_mixed_fraction


def test_safe_eval_basic_arithmetic():
    assert safe_eval("1+2*3-4/2") == 5


def test_safe_eval_division_and_normalization():
    assert safe_eval("5/2") == 2.5
    assert safe_eval("2.0") == 2


def test_safe_eval_zero_division():
    with pytest.raises(ZeroDivisionError):
        safe_eval("1/0")


def test_safe_eval_syntax_error():
    with pytest.raises(SyntaxError):
        safe_eval("1++")


def test_safe_eval_length_guard():
    expr = "1" * 101
    with pytest.raises(ValueError):
        safe_eval(expr)


def test_safe_eval_complexity_depth():
    expr = "(" * 62 + "1" + ")" * 62
    with pytest.raises(ValueError):
        safe_eval(expr)


def test_power_operator_behavior(monkeypatch):
    # pow is disallowed by default
    with pytest.raises(ValueError):
        safe_eval("2**3")

    # enable pow
    monkeypatch.setenv("ALLOW_POW", "1")
    assert safe_eval("2**3") == 8

    # exponent too large
    with pytest.raises(ValueError):
        safe_eval("2**21")

    # base too large
    with pytest.raises(ValueError):
        safe_eval("1000001**2")


def test_float_to_mixed_fraction_examples():
    assert float_to_mixed_fraction(1.75) == "1 3/4"
    assert float_to_mixed_fraction(0.5) == "1/2"
    assert float_to_mixed_fraction(2.0) == "2"
    assert float_to_mixed_fraction(-1.25) == "-1 1/4"
    assert float_to_mixed_fraction(0.3333333333333, max_denominator=100) == "1/3"
