import ast
import operator

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.expr) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))  # type: ignore
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))  # type: ignore
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

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise

    # Complexity checks to prevent DoS via huge/deep expressions
    _check_complexity(tree)

    try:
        result = _eval_node(tree.body)
    except RecursionError:
        # Protect against pathological recursion/very deep AST evaluation
        raise ValueError("計算式が複雑すぎます")

    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result
