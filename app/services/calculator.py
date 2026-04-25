import ast
import operator
import os
import re
from fractions import Fraction
from typing import Any, Callable, Dict, cast, Union


def _safe_pow(left: int | float, right: int | float) -> int | float:
    """べき乗演算のガード付き実装。指数・底が大きすぎる場合は ValueError を送出する。"""
    if not isinstance(right, int) or abs(right) > 20:
        raise ValueError("べき乗の指数が大きすぎます")
    if abs(left) > 1e6:
        raise ValueError("べき乗の底が大きすぎます")
    # operator.pow is untyped; cast to expected numeric return
    return cast(int | float, operator.pow(left, right))


_OPS: Dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


Number = Union[int, float, Fraction]

def _eval_node(node: ast.expr, ops: Dict[type, Callable[..., Any]]) -> Number:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
        return ops[type(node.op)](_eval_node(node.operand, ops))  # type: ignore
    if isinstance(node, ast.BinOp) and type(node.op) in ops:
        left = _eval_node(node.left, ops)
        right = _eval_node(node.right, ops)
        # Special-case division to preserve exact rationals when both operands are integers/Fractions
        if type(node.op) is ast.Div:
            # If either is Fraction, convert both to Fraction
            if isinstance(left, Fraction) or isinstance(right, Fraction):
                return Fraction(left) / Fraction(right)  # type: ignore[arg-type]
            if isinstance(left, int) and isinstance(right, int):
                return Fraction(left, right)
            # Fallback to standard operator (may produce float)
            return ops[type(node.op)](left, right)  # type: ignore
        return ops[type(node.op)](left, right)  # type: ignore
    raise ValueError("不正な式")


def _check_complexity(node: ast.AST, max_nodes: int = 2000, max_depth: int = 60) -> None:
    """Traverse the AST and ensure node count and depth are within limits.

    Raises ValueError if limits exceeded.
    """
    count = 0
    maxd = 0

    def dfs(n: ast.AST, depth: int) -> None:
        nonlocal count, maxd
        count += 1
        if depth > maxd:
            maxd = depth
        if count > max_nodes:
            raise ValueError("計算式が複雑すぎます")
        for child in ast.iter_child_nodes(n):
            dfs(child, depth + 1)

    dfs(node, 0)
    if maxd > max_depth:
        raise ValueError("計算式が複雑すぎます")


def safe_eval(expr: str) -> Number:
    # Basic input length guard: normally reject expressions longer than 100 characters.
    # Exception: allow longer inputs when they contain long decimal/repeating notation
    # or mixed-fraction syntax that will be preprocessed into exact Fraction literals.
    if len(expr) > 100:
        long_dec_check = r"(?P<sign>-?)(?P<int>\d+)\.(?P<dec>\d{20,})"
        rep_check = r"(?P<sign>-?)(?P<whole>\d*)\.(?P<nonrep>\d*)\{(?P<rep>\d+)\}"
        mixed_check = r"(?P<sign>[-+]?)(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)"
        if not re.search(long_dec_check, expr) and not re.search(rep_check, expr) and not re.search(mixed_check, expr):
            raise ValueError("計算式が長すぎます")
    # Absolute maximum cap to avoid DoS via extremely large payloads
    if len(expr) > 20000:
        raise ValueError("計算式が長すぎます")

    # Convert very long decimal literals (many digits after decimal point) to exact Fraction literals.
    # Example: 0.000...123 -> (123/1000...)
    def _replace_long_decimal(m: re.Match[str]) -> str:
        sign = m.group("sign") or ""
        intpart = m.group("int")
        decpart = m.group("dec")
        # numerator = concatenation of intpart and decpart
        numerator = int((intpart + decpart))
        denom = 10 ** len(decpart)
        if sign == "-":
            numerator = -numerator
        return f"({numerator}/{denom})"

    # match decimals with 20 or more digits after the decimal point
    long_dec_pattern = r"(?P<sign>-?)(?P<int>\d+)\.(?P<dec>\d{20,})"
    expr = re.sub(long_dec_pattern, _replace_long_decimal, expr)

    # Preprocess repeating decimals like "0.(3)" or "1.2(34)" into rational numer/denom
    def _replace_repeating(m: re.Match[str]) -> str:
        # Groups: sign, whole (may be empty), nonrep (may be empty), rep (required)
        sign = m.group("sign") or ""
        whole = m.group("whole") or ""
        nonrep = m.group("nonrep") or ""
        rep = m.group("rep")
        W = int(whole) if whole != "" else 0
        A = nonrep
        B = rep
        mlen = len(A)
        nlen = len(B)
        if mlen > 0:
            num = int(A) * (10**nlen - 1) + int(B)
            den = (10**mlen) * (10**nlen - 1)
        else:
            num = int(B)
            den = 10**nlen - 1
        total_num = W * den + num
        if sign == "-":
            total_num = -total_num
        # return as a numeric division literal that safe_eval can parse
        return f"({total_num}/{den})"

    # pattern accepting only {...} for repeating decimals
    rep_pattern = r"(?P<sign>-?)(?P<whole>\d*)\.(?P<nonrep>\d*)\{(?P<rep>\d+)\}"
    expr = re.sub(rep_pattern, _replace_repeating, expr)

    # Preprocess mixed fractions like "2 2/3" -> "(2 + 2/3)" and negatives "-1 1/4" -> "- (1 + 1/4)"
    def _replace_mixed(m: re.Match[str]) -> str:
        sign = m.group("sign") or ""
        whole = m.group("whole")
        num = m.group("num")
        den = m.group("den")
        if sign == "-":
            # -1 1/4 means -(1 + 1/4)
            return f"(-({whole} + {num}/{den}))"
        # positive or no sign
        return f"({whole} + {num}/{den})"

    pattern = r"(?P<sign>[-+]?)(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)"
    expr = re.sub(pattern, _replace_mixed, expr)

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise

    # Complexity checks to prevent DoS via huge/deep expressions
    _check_complexity(tree)

    # Build operator mapping per-invocation. Power operator is opt-in via ALLOW_POW env var.
    # _safe_pow enforces limits on exponent and base to prevent huge results.
    ops = _OPS.copy()
    allow_pow = os.getenv("ALLOW_POW", "0").lower() in ("1", "true", "yes")
    if allow_pow:
        ops[ast.Pow] = _safe_pow

    try:
        result = _eval_node(tree.body, ops)
    except RecursionError:
        # Protect against pathological recursion/very deep AST evaluation
        raise ValueError("計算式が複雑すぎます")

    # Normalize exact integers
    if isinstance(result, float) and result.is_integer():
        return int(result)
    if isinstance(result, Fraction) and result.denominator == 1:
        return result.numerator
    return result


def float_to_mixed_fraction(value: Union[int, float, Fraction], max_denominator: int = 1000) -> str:
    """Convert an int/float/Fraction to a mixed fraction string (帯分数).

    If given a float, it's converted to a Fraction via limit_denominator to avoid
    extremely large denominators. If given a Fraction, use it directly to preserve
    exactness (so very large denominators are shown in the preview).
    """
    if value == 0:
        return "0"
    sign = "-" if (value < 0) else ""
    if isinstance(value, Fraction):
        frac = value
        if frac < 0:
            frac = -frac
    else:
        frac = Fraction(value).limit_denominator(max_denominator)
    num = frac.numerator
    den = frac.denominator
    whole, rem = divmod(abs(num), den)
    if rem == 0:
        return f"{sign}{whole}"
    if whole == 0:
        return f"{sign}{rem}/{den}"
    return f"{sign}{whole} {rem}/{den}"


def mixed_fraction_parts(value: Union[int, float, Fraction], max_denominator: int = 1000) -> dict[str, int | str]:
    """Return mixed fraction parts for HTML rendering.

    Accepts int/float/Fraction. If a Fraction is provided, it's used directly.
    """
    if isinstance(value, Fraction):
        frac = value
    else:
        frac = Fraction(value).limit_denominator(max_denominator)
    num = frac.numerator
    den = frac.denominator
    sign = "-" if num < 0 else ""
    num_abs = abs(num)
    whole = num_abs // den
    rem = num_abs % den
    return {"sign": sign, "whole": whole, "num": rem, "den": den}


def fraction_to_repeating_decimal(frac: Fraction | int | float, max_len: int = 1000) -> str:
    """Convert a Fraction to a decimal string, using braces for repeating part.

    Produces up to `max_len` decimal digits (no rounding). If the decimal terminates
    within max_len digits, the full terminating decimal is returned. If a repeating
    cycle is detected within the limit, the repeating part is returned using braces
    (e.g. "0.{3}"). If the digit limit is reached without detecting a repeat, the
    decimal digits are truncated (no rounding) and returned as-is.
    """
    if not isinstance(frac, Fraction):
        frac = Fraction(frac)

    num = frac.numerator
    den = frac.denominator
    sign = "-" if num < 0 else ""
    num = abs(num)

    whole = num // den
    rem = num % den

    if rem == 0:
        return f"{sign}{whole}"

    # Long division to produce decimal digits and detect repeating remainder
    decimals: list[str] = []
    seen: dict[int, int] = {}
    idx = 0
    repeat_start: int | None = None
    while rem != 0 and idx < max_len:
        if rem in seen:
            repeat_start = seen[rem]
            break
        seen[rem] = idx
        rem *= 10
        digit = rem // den
        decimals.append(str(digit))
        rem = rem % den
        idx += 1

    if rem == 0:
        # terminating decimal
        return f"{sign}{whole}." + ("".join(decimals) if decimals else "0")

    # If limit reached without finding a repeating start, return truncated digits
    if repeat_start is None:
        return f"{sign}{whole}." + "".join(decimals)

    # repeating — use braces instead of parentheses
    non_rep = "".join(decimals[:repeat_start])
    rep = "".join(decimals[repeat_start:])
    if non_rep == "":
        return f"{sign}{whole}.{{{rep}}}"
    return f"{sign}{whole}.{non_rep}{{{rep}}}"


def float_to_repeating_decimal(value: Union[int, float, Fraction], max_len: int = 1000) -> str:
    # For float inputs, approximate to a reasonable denominator so common fractions
    # like 1/3 are detected. Use limit_denominator to avoid exposing raw binary float
    # representations; cap the denominator to keep behaviour stable.
    if isinstance(value, Fraction):
        frac = value
    else:
        frac = Fraction(value).limit_denominator(1000)
    return fraction_to_repeating_decimal(frac, max_len=max_len)


def format_result(result: Number, show_fraction: bool) -> int | float | str:
    """Format a calculation result for display.

    If show_fraction is True and result is numeric, convert to mixed-fraction string.
    Otherwise, return a decimal string representation without rounding (up to 1000 digits),
    using braces for repeating parts when applicable. To preserve API compatibility,
    short terminating decimals are returned as numeric (float) when safe.
    """
    if show_fraction and isinstance(result, (int, float, Fraction)):
        return float_to_mixed_fraction(result)
    # For numeric results, prefer exact integer when possible.
    if isinstance(result, (int, float, Fraction)):
        frac = Fraction(result) if not isinstance(result, Fraction) else result
        if frac.denominator == 1:
            return frac.numerator
        # Produce decimal representation up to limit
        rep = float_to_repeating_decimal(result, max_len=1000)
        if "{" in rep:
            return rep
        # terminating decimal string: decide whether to return numeric or string
        if "." in rep:
            dec_part = rep.split(".", 1)[1]
            # If decimal part is short, return a float for API compatibility
            if len(dec_part) <= 15:
                try:
                    return float(rep)
                except Exception:
                    return rep
        # long terminating decimal -> return string (no rounding)
        return rep
    return result
