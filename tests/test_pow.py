import importlib

import pytest


def reload_calc_with_env(monkeypatch, allow_pow_value: str):
    monkeypatch.setenv("ALLOW_POW", allow_pow_value)
    import app.services.calculator as calcmod

    importlib.reload(calcmod)
    return calcmod


def test_pow_disallowed_by_default(monkeypatch):
    calcmod = reload_calc_with_env(monkeypatch, "0")
    with pytest.raises(ValueError):
        calcmod.Calculator().safe_eval("2 ** 3")


def test_pow_allowed(monkeypatch):
    calcmod = reload_calc_with_env(monkeypatch, "1")
    assert calcmod.Calculator().safe_eval("2 ** 3") == 8


def test_pow_large_exponent_rejected(monkeypatch):
    calcmod = reload_calc_with_env(monkeypatch, "1")
    with pytest.raises(ValueError):
        calcmod.Calculator().safe_eval("2 ** 100")
