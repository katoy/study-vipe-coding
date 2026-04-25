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

Implementation notes

- 計算ロジックは `Calculator` クラスとして実装されており、プログラムからは `from app.services.calculator import Calculator` を使ってインスタンスを生成して利用できます。アプリ本体は起動時に `app.main.calc` として共有インスタンスを作成します。ユニットテストからアプリ内部の動作を差し替える際は `app.main.calc` のメソッドをモックするのが簡単です。
- べき乗（`**` / ast.Pow）はデフォルトで無効です。動作させるには環境変数 `ALLOW_POW=1` を設定してください。実装側で指数・底の上限チェックを行い、大きな計算結果やリソース枯渇を防止しています。
- API のレートリミットは `RATE_LIMIT_PER_MIN` で制御できます（デフォルト 60）。現在の実装は単一プロセス向けの in-memory 実装のため、水平スケール環境では外部ストア（例: Redis）を用いることを推奨します。
- Jinja2 のテンプレートキャッシュは開発環境で無効化されています（`templates.env.cache = {}`）。本番での最適化が必要な場合は適切なキャッシュ設定を検討してください.
