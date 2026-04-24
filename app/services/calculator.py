import ast
import operator
import os
import re
from typing import Any, Callable, Dict

_OPS: Dict[type, Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.expr, ops: Dict[type, Callable[..., Any]]) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
        return ops[type(node.op)](_eval_node(node.operand, ops))  # type: ignore
    if isinstance(node, ast.BinOp) and type(node.op) in ops:
        left = _eval_node(node.left, ops)
        right = _eval_node(node.right, ops)
        # Special guarding for power operator to avoid huge results
        if type(node.op) is ast.Pow:
            # Only allow reasonably small integer exponents
            if not isinstance(right, int) or abs(right) > 20:
                raise ValueError("べき乗の指数が大きすぎます")
            if abs(left) > 1e6:
                raise ValueError("べき乗の底が大きすぎます")
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


def safe_eval(expr: str) -> int | float:
    # Basic input length guard
    if len(expr) > 100:
        raise ValueError("計算式が長すぎます")

    # Preprocess repeating decimals like "0.(3)" or "1.2(34)" into rational numer/denom
    def _replace_repeating(m: re.Match) -> str:
        # Groups: sign, whole (may be empty), nonrep (may be empty), rep (required)
        sign = m.group('sign') or ''
        whole = m.group('whole') or ''
        nonrep = m.group('nonrep') or ''
        rep = m.group('rep')
        W = int(whole) if whole != '' else 0
        A = nonrep
        B = rep
        mlen = len(A)
        nlen = len(B)
        if mlen > 0:
            num = int(A) * (10**nlen - 1) + int(B)
            den = (10**mlen) * (10**nlen - 1)
        else:
            num = int(B)
            den = (10**nlen - 1)
        total_num = W * den + num
        if sign == '-':
            total_num = -total_num
        # return as a numeric division literal that safe_eval can parse
        return f'({total_num}/{den})'

    # pattern accepting (...) or {...}
    rep_pattern = (
        r"(?P<sign>-?)(?P<whole>\d*)\.(?P<nonrep>\d*)"
        r"(?:\((?P<rep1>\d+)\)|\{(?P<rep2>\d+)\})"
    )

    def _rep_wrapper(m: re.Match) -> str:
        # normalize rep from either group
        rep = m.group('rep1') or m.group('rep2')
        # Build a tiny object with .group for _replace_repeating
        class M:
            def __init__(self, sign, whole, nonrep, rep):
                self._d = {'sign': sign, 'whole': whole, 'nonrep': nonrep, 'rep': rep}
            def group(self, name):
                return self._d.get(name)
        return _replace_repeating(M(m.group('sign'), m.group('whole'), m.group('nonrep'), rep))

    expr = re.sub(rep_pattern, _rep_wrapper, expr)

    # Preprocess mixed fractions like "2 2/3" -> "(2 + 2/3)" and negatives "-1 1/4" -> "- (1 + 1/4)"
    def _replace_mixed(m: re.Match) -> str:
        sign = m.group('sign') or ''
        whole = m.group('whole')
        num = m.group('num')
        den = m.group('den')
        if sign == '-':
            # -1 1/4 means -(1 + 1/4)
            return f'(-({whole} + {num}/{den}))'
        # positive or no sign
        return f'({whole} + {num}/{den})'

    pattern = r"(?P<sign>[-+]?)(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)"
    expr = re.sub(pattern, _replace_mixed, expr)

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise

    # Complexity checks to prevent DoS via huge/deep expressions
    _check_complexity(tree)

    # Build operator mapping per-invocation. Power operator is opt-in via ALLOW_POW env var.
    ops = _OPS.copy()
    allow_pow = os.getenv("ALLOW_POW", "0").lower() in ("1", "true", "yes")
    if allow_pow:
        ops[ast.Pow] = operator.pow

    try:
        result = _eval_node(tree.body, ops)
    except RecursionError:
        # Protect against pathological recursion/very deep AST evaluation
        raise ValueError("計算式が複雑すぎます")

    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result


def float_to_mixed_fraction(value: float, max_denominator: int = 1000) -> str:
    """Convert a numeric value to a mixed fraction string (帯分数).

    Examples:
      1.75 -> "1 3/4"
      0.5  -> "1/2"
      2.0  -> "2"
      -1.25 -> "-1 1/4"
    """
    from fractions import Fraction

    # Use Fraction to obtain a rational approximation within a denominator limit
    frac = Fraction(value).limit_denominator(max_denominator)
    num = frac.numerator
    den = frac.denominator
    sign = "-" if num < 0 else ""
    num_abs = abs(num)
    whole = num_abs // den
    rem = num_abs % den

    if rem == 0:
        return f"{sign}{whole}"
    if whole == 0:
        return f"{sign}{rem}/{den}"
    return f"{sign}{whole} {rem}/{den}"


def fraction_to_repeating_decimal(frac, max_len: int = 50) -> str:
    """Convert a Fraction to a decimal string, using braces for repeating part.

    Examples:
      Fraction(1,3) -> "0.{3}"
      Fraction(8,3) -> "2.{6}"
      Fraction(1,2) -> "0.5"  # terminating
    """
    from fractions import Fraction

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
    decimals = []
    seen = { }
    idx = 0
    repeat_start = None
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

    # repeating — use braces instead of parentheses
    non_rep = "".join(decimals[:repeat_start])
    rep = "".join(decimals[repeat_start:])
    if non_rep == "":
        return f"{sign}{whole}.{{{rep}}}"
    return f"{sign}{whole}.{non_rep}{{{rep}}}"


def float_to_repeating_decimal(value: float, max_denominator: int = 1000) -> str:
    from fractions import Fraction
    frac = Fraction(value).limit_denominator(max_denominator)
    return fraction_to_repeating_decimal(frac)
