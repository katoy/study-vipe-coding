import pytest

from app.services.calculator import float_to_mixed_fraction, safe_eval


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


def test_non_numeric_constant_raises():
    # Strings and other constants should not be allowed
    with pytest.raises(ValueError):
        safe_eval("'hi'")


def test_name_node_raises():
    # Names are not allowed (should raise ValueError)
    with pytest.raises(ValueError):
        safe_eval("abc")


def test_unary_ops():
    assert safe_eval("-3") == -3
    assert safe_eval("+4") == 4


def test_float_zero_fraction():
    assert float_to_mixed_fraction(0.0) == "0"


def test_safe_eval_mixed_fraction_input():
    # Support inputs like "2 2/3+3" which mean 2 + 2/3 + 3
    res = safe_eval("2 2/3+3")
    assert abs(res - (17 / 3)) < 1e-9


def test_safe_eval_negative_mixed_fraction_input():
    # Negative mixed fraction like "-1 1/4 + 2" should be parsed as -(1 + 1/4) + 2
    res = safe_eval("-1 1/4 + 2")
    assert abs(res - 0.75) < 1e-9


def test_fraction_to_repeating_decimal_examples():
    from fractions import Fraction

    from app.services.calculator import float_to_repeating_decimal, fraction_to_repeating_decimal

    assert fraction_to_repeating_decimal(Fraction(1, 3)) == "0.(3)"
    assert fraction_to_repeating_decimal(Fraction(8, 3)) == "2.(6)"
    assert fraction_to_repeating_decimal(Fraction(1, 2)) == "0.5"
    assert fraction_to_repeating_decimal(Fraction(-1, 3)) == "-0.(3)"

    # float conversion via limit_denominator
    assert float_to_repeating_decimal(1.0 / 3.0) == "0.(3)"
    assert float_to_repeating_decimal(0.5) == "0.5"


def test_fraction_to_repeating_decimal_integer_input():
    from app.services.calculator import fraction_to_repeating_decimal

    assert fraction_to_repeating_decimal(2) == "2"


def test_fraction_to_repeating_decimal_nonrep_part():
    from fractions import Fraction

    from app.services.calculator import float_to_repeating_decimal, fraction_to_repeating_decimal

    # 1/6 = 0.1666... -> 0.1(6)
    assert fraction_to_repeating_decimal(Fraction(1, 6)) == "0.1(6)"
    assert float_to_repeating_decimal(1.0 / 6.0) == "0.1(6)"
