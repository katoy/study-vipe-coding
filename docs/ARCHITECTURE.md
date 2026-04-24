アーキテクチャ概要

- フロントエンド: Jinja2 テンプレート + HTMX による部分更新
- バックエンド: FastAPI（app.main）
- コアロジック: app.services.calculator に AST ベースの安全な式評価を実装
- テスト: pytest（単体・統合）、Playwright（E2E）
- 実行: 単一プロセス想定の in-memory レート制限。分散環境では Redis 等に置換する

主要モジュール:
- app.main: ルーティング、ミドルウェア（CORS、rate-limit）
- app.services.calculator: safe_eval、複雑性ガード
- app.templates: index.html / result.html（HTMX 部分更新）
