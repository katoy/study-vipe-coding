from fractions import Fraction
from typing import Any

import pytest

from app.services.calculator import Calculator

calc = Calculator()


def test_safe_eval_basic_arithmetic() -> None:
    assert calc.safe_eval("1+2*3-4/2") == 5


def test_safe_eval_division_and_normalization() -> None:
    assert calc.safe_eval("5/2") == Fraction(5, 2)
    assert calc.safe_eval("2.0") == 2


def test_safe_eval_decimal_arithmetic_keeps_exact_value() -> None:
    assert calc.safe_eval("0.1 + 0.2") == Fraction(3, 10)
    assert calc.safe_eval("0.00001 * 0.00001") == Fraction(1, 10**10)


def test_safe_eval_zero_division() -> None:
    with pytest.raises(ZeroDivisionError):
        calc.safe_eval("1/0")


def test_safe_eval_syntax_error() -> None:
    with pytest.raises(SyntaxError):
        calc.safe_eval("1++")


def test_safe_eval_length_guard() -> None:
    expr = "1" * 101
    with pytest.raises(ValueError):
        calc.safe_eval(expr)


def test_safe_eval_complexity_depth() -> None:
    expr = "(" * 62 + "1" + ")" * 62
    with pytest.raises(ValueError):
        calc.safe_eval(expr)


def test_power_operator_behavior(monkeypatch: Any) -> None:
    # pow is disallowed by default
    with pytest.raises(ValueError):
        Calculator().safe_eval("2**3")

    # enable pow
    monkeypatch.setenv("ALLOW_POW", "1")
    assert Calculator().safe_eval("2**3") == 8

    # exponent too large
    with pytest.raises(ValueError):
        Calculator().safe_eval("2**21")

    # base too large
    with pytest.raises(ValueError):
        Calculator().safe_eval("1000001**2")


def test_mixed_fraction_examples() -> None:
    assert calc.fraction_to_mixed_fraction(Fraction(7, 4)) == "1 3/4"
    assert calc.fraction_to_mixed_fraction(Fraction(1, 2)) == "1/2"
    assert calc.fraction_to_mixed_fraction(Fraction(2, 1)) == "2"
    assert calc.fraction_to_mixed_fraction(Fraction(-5, 4)) == "-1 1/4"
    assert calc.fraction_to_mixed_fraction(Fraction(1, 3), max_denominator=100) == "1/3"


def test_non_numeric_constant_raises() -> None:
    with pytest.raises(ValueError):
        calc.safe_eval("'hi'")


def test_bool_constant_raises() -> None:
    with pytest.raises(ValueError):
        calc.safe_eval("True")


def test_name_node_raises() -> None:
    with pytest.raises(ValueError):
        calc.safe_eval("abc")


def test_unary_ops() -> None:
    assert calc.safe_eval("-3") == -3
    assert calc.safe_eval("+4") == 4


def test_zero_fraction() -> None:
    assert calc.fraction_to_mixed_fraction(Fraction(0, 1)) == "0"


def test_safe_eval_mixed_fraction_input() -> None:
    res = calc.safe_eval("2 2/3+3")
    assert res == Fraction(17, 3)


def test_safe_eval_negative_mixed_fraction_input() -> None:
    res = calc.safe_eval("-1 1/4 + 2")
    assert res == Fraction(3, 4)


def test_fraction_to_repeating_decimal_examples() -> None:
    calc_local = Calculator()
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 3)) == "0.{3}"
    assert calc_local.fraction_to_repeating_decimal(Fraction(8, 3)) == "2.{6}"
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 2)) == "0.5"
    assert calc_local.fraction_to_repeating_decimal(Fraction(-1, 3)) == "-0.{3}"


def test_safe_eval_repeating_nonrep_part() -> None:
    res = calc.safe_eval("1.2{34}")
    assert res == Fraction(611, 495)
    res2 = calc.safe_eval("-1.2{34}")
    assert res2 == Fraction(-611, 495)


def test_fraction_to_repeating_decimal_integer_input() -> None:
    assert Calculator().fraction_to_repeating_decimal(2) == "2"


def test_fraction_to_repeating_decimal_nonrep_part() -> None:
    calc_local = Calculator()
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 6)) == "0.1{6}"


def test_repeating_decimal_small_nonzero_decimal() -> None:
    calc_local = Calculator()
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 10000)) == "0.0001"
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 10**20)) == "0.00000000000000000001"


def test_mixed_fraction_small_nonzero_decimal() -> None:
    calc_local = Calculator()
    assert calc_local.fraction_to_mixed_fraction(Fraction(1, 10**10)) == "1/10000000000"
    assert calc_local.mixed_fraction_parts(Fraction(1, 10**10)) == {
        "sign": "",
        "whole": 0,
        "num": 1,
        "den": 10000000000,
    }


def test_safe_eval_preserves_decimal_literal_precision() -> None:
    calc_local = Calculator()
    result = calc_local.safe_eval("0.100001")
    assert result == Fraction(100001, 1000000)


def test_safe_eval_repeating_decimal_display_can_be_reused() -> None:
    calc_local = Calculator()
    display = calc_local.fraction_to_repeating_decimal(calc_local.safe_eval("1/3267"))
    assert calc_local.safe_eval(f"{display}*2") == Fraction(2, 3267)


def test_safe_eval_parenthesized_repeating_decimal_rejected() -> None:
    with pytest.raises((SyntaxError, ValueError)):
        calc.safe_eval("0.(3)")
