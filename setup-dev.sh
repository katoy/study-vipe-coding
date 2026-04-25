#!/bin/sh
set -e
# Setup development helpers: install pre-commit and enable repository hooks
echo "Installing pre-commit and configuring git hooks..."
python3 -m pip install --user pre-commit || true
# Install pre-commit hooks (will use .pre-commit-config.yaml)
command -v pre-commit >/dev/null 2>&1 && pre-commit install || echo "pre-commit not found in PATH; it may be installed in user site-packages. Add that to PATH or run 'python -m pre_commit install'"
# Install repository-level .githooks and copy the versioned hook there
mkdir -p .githooks
cp pre-commit-hook.sh .githooks/pre-commit
chmod +x .githooks/pre-commit
# Install pre-push hook to run ruff and mypy before pushing
if [ -f pre-push-hook.sh ]; then
  cp pre-push-hook.sh .githooks/pre-push
  chmod +x .githooks/pre-push
fi

git config core.hooksPath .githooks || true

echo "Done. Local hooks enabled. Commits will run ruff; push will run ruff and mypy."
