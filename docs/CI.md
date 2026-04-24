CI の説明

ワークフロー:
- test-and-lint: 依存同期、ruff、mypy、pytest（coverage生成）
- e2e: main ブランチまたは手動実行で Playwright E2E を実行

成果物:
- coverage.xml をアーティファクトとしてアップロード

注意:
- Playwright のブラウザバイナリは CI 実行時にインストールされる。キャッシュを検討する
