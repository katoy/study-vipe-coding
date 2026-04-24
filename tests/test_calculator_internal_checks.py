import ast

import pytest

from app.services import calculator
from app.services.calculator import _check_complexity, safe_eval


def test_check_complexity_count_exceeded():
    tree = ast.parse("1+2", mode="eval")
    with pytest.raises(ValueError):
        _check_complexity(tree, max_nodes=1, max_depth=60)


def test_check_complexity_depth_exceeded():
    tree = ast.parse("(" * 5 + "1" + ")" * 5, mode="eval")
    with pytest.raises(ValueError):
        _check_complexity(tree, max_nodes=2000, max_depth=0)


def test_recursion_handling(monkeypatch):
    def _raise_recursion(node, ops):
        raise RecursionError()

    monkeypatch.setattr(calculator, "_eval_node", _raise_recursion)
    with pytest.raises(ValueError):
        safe_eval("1+1")
