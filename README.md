# Webベース電卓アプリケーション

軽量な FastAPI + HTMX を用いたシンプルな Web 電卓です。ブラウザ UI と JSON API を提供します。

Table of Contents
- [概要](#概要)
- [クイックスタート](#クイックスタート)
- [ファイル一覧](#ファイル一覧)
- [API 仕様](#api-仕様)
- [テストとカバレッジ](#テストとカバレッジ)
- [デモ動画](#デモ動画)
- [開発環境セットアップ (ローカルフック)](#開発環境セットアップ-ローカルフック)
- [静的解析](#静的解析)
- [実装上の注意](#実装上の注意)
- [貢献・ライセンス](#貢献・ライセンス)

---

## 概要
主なポイント（実装に基づく）

- エントリポイント: `app/main.py`
  - HTML UI: GET `/` -> templates/index.html
  - フォーム計算: POST `/calculate` -> templates/result.html（HTMX 部分更新）
  - JSON API: POST `/api/calculate` -> `{ "result": ..., "expression": ... }`
- 計算ロジック: `app/services/calculator.py`
  - Calculator クラスを提供しています: `Calculator()` のインスタンスメソッド（例: `Calculator().safe_eval(expr)`）で式を評価します。アプリ起動時にモジュールレベルの `calc` インスタンスが `app.main` 内に作成されており、アプリケーション実行中にプログラムから再利用する場合は `from app.main import calc` を利用できます。
  - AST ベースの安全な評価を行い、混数、循環小数表記（波括弧 `{}`）等に対応します（内部では `fractions.Fraction` を用いて可能な限り有理数を厳密に扱います）。
  - べき乗は環境変数 `ALLOW_POW` によりオプトイン（安全ガードあり）。
- 簡易レート制限: `RATE_LIMIT_PER_MIN`（単一プロセス向けの in-memory 実装）。
- CORS: `ALLOW_ORIGINS` 環境変数で制御（カンマ区切り）。

---

## クイックスタート

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

---

## API 仕様

- POST /api/calculate
  - リクエスト JSON: `{ "expression": "3/2", "show_fraction": <bool, optional> }`
  - 成功: `200` `{ "result": <数値または文字列>, "expression": "..." }`
  - エラー: `400`（不正な式やゼロ除算など）`{ "error": "...", "expression": "..." }`

OpenAPI（起動中）: `/docs`（Swagger UI）、`/redoc`（ReDoc）

---

## テストとカバレッジ

- ユニットテスト（API・ロジック）

```bash
uv run pytest
```

- E2E（ブラウザ）テストは環境依存のため Docker での実行を推奨します。スクリプト:
  - Windows: `test_ui.bat`
  - macOS/Linux: `bash test_ui.sh`

### カバレッジ計測方法
ローカルでのカバレッジ測定方法:

```bash
# XML と HTML 両方を出力する例
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:coverage_html
```

出力結果は `coverage.xml`（CI 向け）および `coverage_html/`（ブラウザで閲覧可能）に生成されます。

### 現在のカバレッジ結果（リポジトリ内 coverage.xml より）
- 行カバレッジ: 226 / 226 (100%)
- 分岐カバレッジ: 70 / 70 (100%)

(coverage.xml はリポジトリに含まれています)。

---

## デモ動画

デモ用アニメーションは static に配置しています。ブラウザで確認するにはサーバ起動後に以下にアクセスしてください（あるいはリポジトリ内のファイルを参照）:

- `app/static/calculator_demo.gif` — 簡易デモ（GIF）
- `app/static/calculator_demo.webp` — WebP 版

画面を実際に操作するデモを別途用意する場合はここにリンクを追加してください（YouTube 等）。

---

## 開発環境セットアップ (ローカルフック)

- リポジトリには `setup-dev.sh` スクリプトが含まれており、ローカルでの開発支援フックをインストールします。
  - 実行: `./setup-dev.sh`
  - インストールされるフック:
    - `.githooks/pre-commit` : コミット時に `ruff check app tests` を実行します。
    - `.githooks/pre-push` : プッシュ時に `ruff check app tests` と `mypy app` を実行し、失敗すると push をブロックします。

目的: コード品質（Linter / 型チェック）をローカル開発で早期に検出し、CI 前に不整合を防ぐためです。

---

## 静的解析

- Ruff / Mypy を CI として導入しています。ローカルでチェックするコマンド例:

```bash
uv run ruff check app tests
uv run mypy app
```

---

## 実装上の注意

- 計算式は AST による解析で評価され、任意のコード実行はブロックされています（テストで検証済み）。
- レートリミットと CORS の実装はシングルプロセス向けの簡易実装です。本番での水平スケール時は外部ストアや API ゲートウェイを導入してください。

---

## 貢献・ライセンス

PR・Issue を歓迎します。

ライセンスは MIT です（`LICENSE` を参照）。

---
