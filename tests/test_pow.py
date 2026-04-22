import importlib
import os

import pytest


def reload_calc_with_env(monkeypatch, allow_pow_value: str):
    monkeypatch.setenv("ALLOW_POW", allow_pow_value)
    import app.services.calculator as calc
    importlib.reload(calc)
    return calc


def test_pow_disallowed_by_default(monkeypatch):
    calc = reload_calc_with_env(monkeypatch, "0")
    with pytest.raises(ValueError):
        calc.safe_eval("2 ** 3")


def test_pow_allowed(monkeypatch):
    calc = reload_calc_with_env(monkeypatch, "1")
    assert calc.safe_eval("2 ** 3") == 8


def test_pow_large_exponent_rejected(monkeypatch):
    calc = reload_calc_with_env(monkeypatch, "1")
    with pytest.raises(ValueError):
        calc.safe_eval("2 ** 100")
