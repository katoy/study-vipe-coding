Development setup
=================

This repository includes local and CI-side lint checks to ensure code quality. To make local development enforce the same lint checks before commits, follow these steps:

1. Enable repository hooks and install pre-commit tools

```sh
# Run once after cloning
./setup-dev.sh
```

This will:
- install pre-commit (to run the configured hooks from .pre-commit-config.yaml)
- create a .githooks directory and copy a versioned pre-commit script (pre-commit-hook.sh) there
- set git config core.hooksPath .githooks

2. What the pre-commit hook does

- The pre-commit hook runs `ruff check app tests` and will abort the commit if ruff reports issues.
- The project already runs the same checks in CI; this ensures you don't commit failing lint locally.

3. If pre-commit auto-fix is desired

- You can run `uv run ruff format app tests` (preferred if you use the uv wrapper) or `ruff format app tests` to auto-fix many problems before committing.

4. Notes

- The pre-commit framework is optional; the repository also ships a versioned shell hook `pre-commit-hook.sh` which the setup script installs to `.githooks/pre-commit`.
- For CI, the GitHub Actions already runs ruff checks and will fail PRs if linting fails.
