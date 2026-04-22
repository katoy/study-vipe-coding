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


def safe_eval(expr: str) -> int | float:
    if len(expr) > 100:
        raise ValueError("計算式が長すぎます")
    tree = ast.parse(expr, mode="eval")
    result = _eval_node(tree.body)
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result
