影響範囲と依存

1. ランタイム/依存パッケージ
- Python >= 3.12
- fastapi, uvicorn, jinja2, httpx
- 開発: pytest, pytest-playwright, playwright, ruff, mypy, pytest-cov

2. 外部サービス
- 現状: なし（全てアプリ内で完結）。将来的に分散レートリミットや監視を導入する場合は Redis, Prometheus 等を検討

3. 環境変数
- ALLOW_ORIGINS: CORS 許可リスト
- ALLOW_POW: べき乗機能のON/OFF
- RATE_LIMIT_PER_MIN: APIレート制限の上限

4. インフラ / 実行環境
- 単一プロセス想定の in-memory rate limiter。複数ワーカーや水平スケール時は外部ストアに置換必須
- Docker イメージ化、Compose によるローカルデプロイをサポート

5. 互換性/将来対応
- Python 3.12 を最小サポート。将来のメジャーバージョンアップ時は互換性テストを追加
- Playwright ブラウザバイナリの更新は CI キャッシュを検討

6. セキュリティ観点
- safe_eval による式の安全性担保が必須
- CORS のワイルドカード回避、ALLOWED_ORIGINS の運用
