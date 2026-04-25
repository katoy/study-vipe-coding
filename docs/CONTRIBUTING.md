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

ローカルフックのセットアップ

開発者がローカルで簡単に品質チェックを実行できるよう、リポジトリに `setup-dev.sh` を用意しています。

1. フックのインストール

```sh
./setup-dev.sh
```

2. インストールされる主なフック

- `.githooks/pre-commit` : コミット時に `ruff check app tests` を実行します（自動でコミットをブロックします）。
- `.githooks/pre-push` : プッシュ時に `ruff check app tests` と `mypy app` を実行します。失敗すると push を中止します。

目的: コード品質を早期に検出し、CI 前に不整合を修正するためです。CI 上では push 時に ruff + mypy を走らせ、PR（pull request）時に pytest を実行する設定になっています。

PR テンプレート: .github/PULL_REQUEST_TEMPLATE.md を参照
