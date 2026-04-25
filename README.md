# Webベース電卓アプリケーション

軽量な FastAPI + HTMX を用いたシンプルな Web 電卓です。ブラウザ UI と JSON API を提供します。

主なポイント（実装に基づく）
- エントリポイント: `app/main.py`
  - HTML UI: GET `/` -> templates/index.html
  - フォーム計算: POST `/calculate` -> templates/result.html（HTMX 部分更新）
  - JSON API: POST `/api/calculate` -> `{ "result": ..., "expression": ... }`
- 計算ロジック: `app/services/calculator.py`
  - AST ベースの安全な評価 (`safe_eval`)。混数、循環小数表記（波括弧 `{}`）等に対応。
  - べき乗は環境変数 `ALLOW_POW` によりオプトイン（安全ガードあり）。
- 簡易レート制限: `RATE_LIMIT_PER_MIN`（単一プロセス向けの in-memory 実装）。
- CORS: `ALLOW_ORIGINS` 環境変数で制御（カンマ区切り）。

クイックスタート

1. クローンして移動

```bash
git clone <リポジトリURL>
cd study-vipe-coding
```

2. 依存関係（uv を用いる想定）

```bash
uv sync
```

3. 開発用サーバー起動

```bash
uv run uvicorn app.main:app --reload --port 8000
```

ブラウザで `http://localhost:8000` を開くと UI が表示されます。

API 仕様（簡潔）

- POST /api/calculate
  - リクエスト JSON: `{ "expression": "3/2", "show_fraction": <bool, optional> }`
  - 成功: `200` `{ "result": <数値または文字列>, "expression": "..." }`
  - エラー: `400`（不正な式やゼロ除算など）`{ "error": "...", "expression": "..." }`

ドキュメント

- OpenAPI（起動中）: `/docs`（Swagger UI）、`/redoc`（ReDoc）

テスト

- ユニットテスト（API・ロジック）

```bash
uv run pytest
```

- E2E（ブラウザ）テストは環境依存のため Docker での実行を推奨します。スクリプト:
  - Windows: `test_ui.bat`
  - macOS/Linux: `bash test_ui.sh`

（ローカルで直接 Playwright を使う場合の手順は tests/ と既存のスクリプトを参照してください）

静的解析

- Ruff / Mypy を CI として導入しています。ローカルでチェックするコマンド例:

```bash
uv run ruff check app tests
uv run mypy app
```

環境変数（主なもの）

- ALLOW_ORIGINS: CORS 許可オリジン（カンマ区切り）。デフォルトは `http://localhost:8000`。
- ALLOW_POW: べき乗許可（`1`, `true`, `yes` で有効）。デフォルトは無効。
- RATE_LIMIT_PER_MIN: API の1分当たりリクエスト上限（デフォルト `60`）。

実装上の注意

- 計算式は AST による解析で評価され、任意のコード実行はブロックされています（テストで検証済み）。
- レートリミットと CORS の実装はシングルプロセス向けの簡易実装です。本番での水平スケール時は外部ストアや API ゲートウェイを導入してください。

貢献・ライセンス

PR・Issue を歓迎します。

開発環境セットアップ（ローカルフック）

- リポジトリには `setup-dev.sh` スクリプトが含まれており、ローカルでの開発支援フックをインストールします。
  - 実行: `./setup-dev.sh`
  - インストールされるフック:
    - `.githooks/pre-commit` : コミット時に `ruff check app tests` を実行します。
    - `.githooks/pre-push` : プッシュ時に `ruff check app tests` と `mypy app` を実行し、失敗すると push をブロックします。

- 目的: コード品質（Linter / 型チェック）をローカル開発で早期に検出し、CI 前に不整合を防ぐためです。

- 備考: `setup-dev.sh` は実行環境に `pre-commit` をインストールし、`.githooks` を git の hooksPath として設定します。CI は引き続き別途動作します。

ライセンスは MIT です（`LICENSE` を参照）。

---

## ファイル一覧
主要なファイル・ディレクトリと役割:

- app/
  - main.py - FastAPI アプリケーションのエントリポイント（ルーティング、テンプレート応答、API）。
  - services/calculator.py - 計算ロジックと表示用ヘルパー（安全な AST 評価、Fraction ベースの扱い、分数/循環小数の生成）。
  - templates/ - Jinja2 テンプレート（index.html, result.html）。
  - static/ - 静的資産（favicon.svg、demo GIF など）。
- tests/ - ユニットテスト群（pytest）。
- docs/ - ドキュメント（OpenAPI 等。存在する場合）。
- setup-dev.sh - ローカル開発用フックのインストールスクリプト。
- .github/workflows/ - CI 設定（lint / test ワークフロー）。

## カバレッジ計測方法
ローカルでのカバレッジ測定方法:

1. pytest と coverage を使って実行（例）:

```bash
# XML と HTML 両方を出力する例
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:coverage_html
```

2. 出力結果は `coverage.xml`（CI 向け）および `coverage_html/`（ブラウザで閲覧可能）に生成されます。

※ 本リポジトリではテスト実行時に coverage を生成する CI 設定がある場合があります。ローカルでの実行は上記コマンドを推奨します。

### 現在のカバレッジ結果（リポジトリ内 coverage.xml より）
- 行カバレッジ: 226 / 226 (100%)
- 分岐カバレッジ: 70 / 70 (100%)

（coverage.xml をリポジトリに含めています。最新の結果は CI 実行やローカル測定で再生成してください。）

## デモ動画
デモ用アニメーションは static に配置しています。ブラウザで確認するにはサーバ起動後に以下にアクセスしてください（あるいはリポジトリ内のファイルを参照）:

- `app/static/calculator_demo.gif` — 簡易デモ（GIF）
- `app/static/calculator_demo.webp` — WebP 版

画面を実際に操作するデモを別途用意する場合はここにリンクを追加してください（YouTube 等）。

---
