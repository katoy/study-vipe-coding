import ast

import pytest

from app.services import calculator


def test_check_complexity_count_exceeded():
    tree = ast.parse("1+2", mode="eval")
    calc = calculator.Calculator()
    with pytest.raises(ValueError):
        calc._check_complexity(tree, max_nodes=1, max_depth=60)


def test_check_complexity_depth_exceeded():
    tree = ast.parse("(" * 5 + "1" + ")" * 5, mode="eval")
    calc = calculator.Calculator()
    with pytest.raises(ValueError):
        calc._check_complexity(tree, max_nodes=2000, max_depth=0)


def test_recursion_handling(monkeypatch):
    def _raise_recursion(self, node, ops):
        raise RecursionError()

    monkeypatch.setattr(calculator.Calculator, "_eval_node", _raise_recursion)
    with pytest.raises(ValueError):
        calculator.Calculator().safe_eval("1+1")
