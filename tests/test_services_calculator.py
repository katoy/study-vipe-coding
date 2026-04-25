import pytest

from app.services.calculator import Calculator


calc = Calculator()


def test_safe_eval_basic_arithmetic():
    assert calc.safe_eval("1+2*3-4/2") == 5


def test_safe_eval_division_and_normalization():
    assert calc.safe_eval("5/2") == 2.5
    assert calc.safe_eval("2.0") == 2


def test_safe_eval_zero_division():
    with pytest.raises(ZeroDivisionError):
        calc.safe_eval("1/0")


def test_safe_eval_syntax_error():
    with pytest.raises(SyntaxError):
        calc.safe_eval("1++")


def test_safe_eval_length_guard():
    expr = "1" * 101
    with pytest.raises(ValueError):
        calc.safe_eval(expr)


def test_safe_eval_complexity_depth():
    expr = "(" * 62 + "1" + ")" * 62
    with pytest.raises(ValueError):
        calc.safe_eval(expr)


def test_power_operator_behavior(monkeypatch):
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


def test_float_to_mixed_fraction_examples():
    assert calc.float_to_mixed_fraction(1.75) == "1 3/4"
    assert calc.float_to_mixed_fraction(0.5) == "1/2"
    assert calc.float_to_mixed_fraction(2.0) == "2"
    assert calc.float_to_mixed_fraction(-1.25) == "-1 1/4"
    assert calc.float_to_mixed_fraction(0.3333333333333, max_denominator=100) == "1/3"


def test_non_numeric_constant_raises():
    with pytest.raises(ValueError):
        calc.safe_eval("'hi'")


def test_name_node_raises():
    with pytest.raises(ValueError):
        calc.safe_eval("abc")


def test_unary_ops():
    assert calc.safe_eval("-3") == -3
    assert calc.safe_eval("+4") == 4


def test_float_zero_fraction():
    assert calc.float_to_mixed_fraction(0.0) == "0"


def test_safe_eval_mixed_fraction_input():
    res = calc.safe_eval("2 2/3+3")
    assert abs(res - (17 / 3)) < 1e-9


def test_safe_eval_negative_mixed_fraction_input():
    res = calc.safe_eval("-1 1/4 + 2")
    assert abs(res - 0.75) < 1e-9


def test_fraction_to_repeating_decimal_examples():
    from fractions import Fraction

    calc_local = Calculator()
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 3)) == "0.{3}"
    assert calc_local.fraction_to_repeating_decimal(Fraction(8, 3)) == "2.{6}"
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 2)) == "0.5"
    assert calc_local.fraction_to_repeating_decimal(Fraction(-1, 3)) == "-0.{3}"

    # float conversion via limit_denominator
    assert calc_local.float_to_repeating_decimal(1.0 / 3.0) == "0.{3}"
    assert calc_local.float_to_repeating_decimal(0.5) == "0.5"


def test_safe_eval_repeating_nonrep_part():
    res = calc.safe_eval("1.2{34}")
    assert abs(res - (611 / 495)) < 1e-9
    res2 = calc.safe_eval("-1.2{34}")
    assert abs(res2 - (-(611 / 495))) < 1e-9


def test_fraction_to_repeating_decimal_integer_input():
    assert Calculator().fraction_to_repeating_decimal(2) == "2"


def test_fraction_to_repeating_decimal_nonrep_part():
    from fractions import Fraction

    calc_local = Calculator()
    assert calc_local.fraction_to_repeating_decimal(Fraction(1, 6)) == "0.1{6}"
    assert calc_local.float_to_repeating_decimal(1.0 / 6.0) == "0.1{6}"
