import importlib
import sys
from importlib import metadata

print("PYTEST_CONFTEMP: sys.path length:", len(sys.path))

try:
    eps = metadata.entry_points()
    pytest_eps = [ep for ep in eps.get("pytest11", [])]
    print("PYTEST_CONFTEMP: pytest11 entry points:", pytest_eps)
except Exception as e:
    print("PYTEST_CONFTEMP: entry_points error:", e)

try:
    mod = importlib.import_module("pytest_playwright")
    print(
        "PYTEST_CONFTEMP: imported pytest_playwright from",
        getattr(mod, "__file__", repr(mod)),
    )
except Exception as e:
    print("PYTEST_CONFTEMP: import pytest_playwright failed:", e)

pytest_plugins = ["pytest_playwright"]
