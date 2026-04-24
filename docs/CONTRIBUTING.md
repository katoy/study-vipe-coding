貢献ガイドライン

開発フロー:
- フィーチャーブランチを作成し PR を送る
- PR は自動テスト（unit, lint, mypy）を通過することが必須

ローカルチェック:
- 依存同期: uv sync
- フォーマット: uv run ruff format --check app tests
- リント: uv run ruff check app tests
- 型チェック: uv run mypy app
- テスト: uv run pytest

PR テンプレート: .github/PULL_REQUEST_TEMPLATE.md を参照
