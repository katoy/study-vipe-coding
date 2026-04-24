#!/bin/sh
set -e
# Versioned hook script: runs ruff lint check before commit and blocks if issues found.
if command -v uv >/dev/null 2>&1; then
  uv run ruff check app tests
else
  ruff check app tests
fi
RC=$?
if [ $RC -ne 0 ]; then
  echo "\n[pre-commit] ruff found issues - please fix them before committing."
  echo "You can auto-fix many issues with: uv run ruff format app tests || ruff format app tests"
  exit $RC
fi
exit 0
