import importlib

try:
    mod = importlib.import_module("pytest_playwright")
    pytest_plugins = ["pytest_playwright"]
except Exception:
    pytest_plugins = []
