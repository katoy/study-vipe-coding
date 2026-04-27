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
  - AST ベースの安全な評価を行い、混数、循環小数表記（波括弧 `{}`）等に対応します。内部計算は `int` と `fractions.Fraction` に限定しており、通常の `float` 演算で起きる丸め誤差や桁落ちは発生しません。
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


### Docker スクリプト

リポジトリには開発者向けに Docker を使った起動・CI 実行スクリプトを用意しています。

- サーバ起動（Linux/macOS）:

```bash
./run.sh
```

- サーバ起動（Windows）:

```powershell
run.bat
```

これらは Docker の `base`（runtime）ステージをビルドしてコンテナを起動します。
ローカル実行では `PORT` が未設定なら 8000 を使い、Cloud Run では割り当てられた `PORT` に従います。

- CI 実行（Linux/macOS）:

```bash
./ci.sh
```

- CI 実行（Windows）:

```powershell
ci.bat
```

CI スクリプトは Docker の `ci` ステージをビルドし、コンテナ内で ruff/mypy/pytest 等のチェックを実行します。Docker 環境が整っていればローカルで CI 相当の検証が可能です。

### Cloud Run

このアプリは Cloud Run 上でもそのまま動かせます。FastAPI が HTML と JSON API の両方を返し、コンテナは Cloud Run が渡す `PORT` で待ち受けます。

デプロイの基本形は、Docker イメージをビルドして Cloud Run にデプロイする構成です。レート制限は in-memory 実装のため、Cloud Run で複数インスタンスに分かれるとインスタンス単位の制限になります。



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

## 循環小数の表現例

本プロジェクトでは循環小数（循環小数部分）を波括弧で表現します（例: 0.{3} は 0.333... を表す）。いくつかの例を示します:

- 1/3  = 0.{3}                            （周期長: 1）
- 1/7  = 0.{142857}                       （周期長: 6）
- 1/17 = 0.{0588235294117647}            （周期長: 16）
- 1/97 = 0.{010309278350515463917525773195876288659793814432989690721649484536082474226804123711340206185567}  （周期長: 96）

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

### 現在のカバレッジ結果（ローカル実行: pytest --cov=app 実行結果）
- 総合行カバレッジ: 94% (315 行中 20 行が未カバー)

ファイル別（抜粋）:
- app/main.py: 99% (88 行中 1 行が未カバー)
- app/services/calculator.py: 92% (227 行中 19 行が未カバー)

coverage レポートはローカルで生成できます。例:

```bash
# XML と HTML を両方出力する例
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html:coverage_html
```

生成された `coverage.xml`（CI 用）や `coverage_html/`（ブラウザで確認可能）を参照してください。

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
- 小数は文字列から `Fraction` に変換して評価しているため、`0.1 + 0.2` や `0.00001 * 0.00001` のような式でも `float` の丸め誤差や桁落ちを起こしません。
- レートリミットと CORS の実装はシングルプロセス向けの簡易実装です。本番での水平スケール時は外部ストアや API ゲートウェイを導入してください。

---

## 貢献・ライセンス

PR・Issue を歓迎します。

ライセンスは MIT です（`LICENSE` を参照）。

---
