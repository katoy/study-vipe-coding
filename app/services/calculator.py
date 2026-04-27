import ast
import operator
import os
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any, Callable, Dict, Union

Number = Union[int, float, Fraction]


class Calculator:
    """Calculator encapsulates expression evaluation and formatting settings."""

    def __init__(
        self,
        max_decimal_digits: int = 1000,
        max_denominator: int = 1000,
        max_expr_length: int = 100,
        max_nodes: int = 2000,
        max_depth: int = 60,
    ) -> None:
        self.max_decimal_digits = max_decimal_digits
        self.max_denominator = max_denominator
        self.max_expr_length = max_expr_length
        self.max_nodes = max_nodes
        self.max_depth = max_depth
        self.MAX_EXPR_LENGTH_ABSOLUTE = 20000
        # operator map
        self._OPS: Dict[type, Callable[..., Any]] = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        allow_pow = os.getenv("ALLOW_POW", "0").lower() in ("1", "true", "yes")
        if allow_pow:
            self._OPS[ast.Pow] = self._safe_pow

    def _safe_pow(self, left: Number, right: Number) -> Number:
        # We only allow integer exponents for safety/simplicity in this context
        is_int_exponent = False
        exponent_val = 0
        if isinstance(right, int):
            is_int_exponent = True
            exponent_val = right
        elif isinstance(right, Fraction) and right.denominator == 1:
            is_int_exponent = True
            exponent_val = right.numerator

        if not is_int_exponent or abs(exponent_val) > 20:
            raise ValueError("べき乗の指数が大きすぎます")
        if abs(float(left)) > 1e6:
            raise ValueError("べき乗の底が大きすぎます")
        return operator.pow(left, right)  # type: ignore

    def _eval_node(self, node: ast.expr, ops: Dict[type, Callable[..., Any]]) -> Number:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
            return ops[type(node.op)](self._eval_node(node.operand, ops))  # type: ignore
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            left = self._eval_node(node.left, ops)
            right = self._eval_node(node.right, ops)
            if type(node.op) is ast.Div:
                if isinstance(left, Fraction) or isinstance(right, Fraction):
                    return Fraction(left) / Fraction(right)
                if isinstance(left, int) and isinstance(right, int):
                    return Fraction(left, right)
                return ops[type(node.op)](left, right)  # type: ignore
            return ops[type(node.op)](left, right)  # type: ignore
        raise ValueError("不正な式")

    def _check_complexity(
        self, node: ast.AST, max_nodes: int | None = None, max_depth: int | None = None
    ) -> None:
        if max_nodes is None:
            max_nodes = self.max_nodes
        if max_depth is None:
            max_depth = self.max_depth
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

    def safe_eval(self, expr: str) -> Number:
        if len(expr) > self.max_expr_length:
            long_dec_check = r"(?P<sign>-?)(?P<int>\d+)\.(?P<dec>\d{20,})"
            rep_check = r"(?P<sign>-?)(?P<whole>\d*)\.(?P<nonrep>\d*)\{(?P<rep>\d+)\}"
            mixed_check = r"(?P<sign>[-+]?)(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)"
            if (
                not re.search(long_dec_check, expr)
                and not re.search(rep_check, expr)
                and not re.search(mixed_check, expr)
            ):
                raise ValueError("計算式が長すぎます")
        if len(expr) > self.MAX_EXPR_LENGTH_ABSOLUTE:
            raise ValueError("計算式が長すぎます")

        def _replace_long_decimal(m: re.Match[str]) -> str:
            sign = m.group("sign") or ""
            intpart = m.group("int")
            decpart = m.group("dec")
            numerator = int((intpart + decpart))
            denom = 10 ** len(decpart)
            if sign == "-":
                numerator = -numerator
            return f"({numerator}/{denom})"

        long_dec_pattern = r"(?P<sign>-?)(?P<int>\d+)\.(?P<dec>\d{20,})"
        expr = re.sub(long_dec_pattern, _replace_long_decimal, expr)

        def _replace_repeating(m: re.Match[str]) -> str:
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
            return f"({total_num}/{den})"

        rep_pattern = r"(?P<sign>-?)(?P<whole>\d*)\.(?P<nonrep>\d*)\{(?P<rep>\d+)\}"
        expr = re.sub(rep_pattern, _replace_repeating, expr)

        def _replace_mixed(m: re.Match[str]) -> str:
            sign = m.group("sign") or ""
            whole = m.group("whole")
            num = m.group("num")
            den = m.group("den")
            if sign == "-":
                return f"(-({whole} + {num}/{den}))"
            return f"({whole} + {num}/{den})"

        pattern = r"(?P<sign>[-+]?)(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)"
        expr = re.sub(pattern, _replace_mixed, expr)

        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError:
            raise

        self._check_complexity(tree)

        ops = self._OPS.copy()

        try:
            result = self._eval_node(tree.body, ops)
        except RecursionError:
            raise ValueError("計算式が複雑すぎます")

        if isinstance(result, float) and result.is_integer():
            return int(result)
        if isinstance(result, Fraction) and result.denominator == 1:
            return result.numerator
        return result

    def float_to_mixed_fraction(
        self, value: Union[int, float, Fraction], max_denominator: int | None = None
    ) -> str:
        if max_denominator is None:
            max_denominator = self.max_denominator
        if value == 0:
            return "0"
        sign = "-" if (value < 0) else ""
        if isinstance(value, Fraction):
            frac = value
            if frac < 0:
                frac = -frac
        else:
            frac = Fraction(value).limit_denominator(max_denominator)
            if frac == 0 and value != 0:
                frac = Fraction(format(value, ".15g"))
        num = frac.numerator
        den = frac.denominator
        whole, rem = divmod(abs(num), den)
        if rem == 0:
            return f"{sign}{whole}"
        if whole == 0:
            return f"{sign}{rem}/{den}"
        return f"{sign}{whole} {rem}/{den}"

    def mixed_fraction_parts(
        self, value: Union[int, float, Fraction], max_denominator: int | None = None
    ) -> dict[str, int | str]:
        if max_denominator is None:
            max_denominator = self.max_denominator
        if isinstance(value, Fraction):
            frac = value
        else:
            frac = Fraction(value).limit_denominator(max_denominator)
            if frac == 0 and value != 0:
                frac = Fraction(format(value, ".15g"))
        num = frac.numerator
        den = frac.denominator
        sign = "-" if num < 0 else ""
        num_abs = abs(num)
        whole = num_abs // den
        rem = num_abs % den
        return {"sign": sign, "whole": whole, "num": rem, "den": den}

    def fraction_to_repeating_decimal(self, frac: Number, max_len: int | None = None) -> str:
        if max_len is None:
            max_len = self.max_decimal_digits
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
            return f"{sign}{whole}." + ("".join(decimals) if decimals else "0")
        if repeat_start is None:
            return f"{sign}{whole}." + "".join(decimals)
        non_rep = "".join(decimals[:repeat_start])
        rep = "".join(decimals[repeat_start:])
        if non_rep == "":
            return f"{sign}{whole}.{{{rep}}}"
        return f"{sign}{whole}.{non_rep}{{{rep}}}"

    def float_to_repeating_decimal(self, value: Number, max_len: int | None = None) -> str:
        if max_len is None:
            max_len = self.max_decimal_digits
        if isinstance(value, Fraction):
            frac = value
        else:
            frac = Fraction(value).limit_denominator(self.max_denominator)
            if frac == 0 and value != 0:
                # Very small non-zero floats can collapse to 0 under limit_denominator().
                # Preserve them as a decimal string instead of losing the value.
                rounded = format(value, ".15g")
                if "e" in rounded or "E" in rounded:
                    return format(Decimal(rounded), "f").rstrip("0").rstrip(".")
                return rounded
        return self.fraction_to_repeating_decimal(frac, max_len=max_len)

    def format_result(self, result: Number, show_fraction: bool) -> Number | str:
        if show_fraction and isinstance(result, (int, float, Fraction)):
            return self.float_to_mixed_fraction(result)
        if isinstance(result, (int, float, Fraction)):
            frac = Fraction(result) if not isinstance(result, Fraction) else result
            if frac.denominator == 1:
                return frac.numerator
            rep = self.float_to_repeating_decimal(result, max_len=self.max_decimal_digits)
            if "{" in rep:
                return rep
            if "." in rep:
                dec_part = rep.split(".", 1)[1]
                if len(dec_part) <= 15:
                    try:
                        return float(rep)
                    except Exception:
                        return rep
            return rep
        return result
