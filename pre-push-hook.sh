#!/bin/sh
set -e
# Versioned pre-push hook: run ruff and mypy before allowing push
if command -v uv >/dev/null 2>&1; then
  uv run ruff check app tests
  uv run mypy app
else
  ruff check app tests
  mypy app
fi

echo "[pre-push] ruff and mypy passed."
exit 0
