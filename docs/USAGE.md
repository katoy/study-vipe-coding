クイックスタート

ローカル開発:
1. 依存を同期
   uv sync
2. 開発サーバー起動
   uv run uvicorn app.main:app --reload --port 8000
3. ブラウザで http://localhost:8000 を開く

テスト:
- 単体テスト: uv run pytest
- E2E (Playwright): uv run pytest tests/test_ui.py （Docker推奨）

Docker:
- ビルド: docker build -t calculator-app .
- 実行: docker run --rm -p 8000:8000 calculator-app

環境変数の主な説明:
- ALLOW_ORIGINS: CORS許可オリジン（カンマ区切り）
- ALLOW_POW: べき乗を有効にする (1/true)
- RATE_LIMIT_PER_MIN: 1分あたりのAPI上限（デフォルト 60）
