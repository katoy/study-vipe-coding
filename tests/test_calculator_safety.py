import pytest

from app.services.calculator import Calculator


def test_pow_disabled_by_default():
    with pytest.raises(ValueError):
        Calculator().safe_eval("2**3")


def test_pow_enabled_small(monkeypatch):
    monkeypatch.setenv("ALLOW_POW", "1")
    assert Calculator().safe_eval("2**3") == 8


def test_pow_large_exponent(monkeypatch):
    monkeypatch.setenv("ALLOW_POW", "1")
    with pytest.raises(ValueError):
        Calculator().safe_eval("2**100")


def test_pow_large_base(monkeypatch):
    monkeypatch.setenv("ALLOW_POW", "1")
    with pytest.raises(ValueError):
        Calculator().safe_eval("1000001**2")


def test_length_guard():
    expr = "1" * 101
    with pytest.raises(ValueError):
        Calculator().safe_eval(expr)
