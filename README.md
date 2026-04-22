# Webベース電卓アプリケーション

![アプリケーションの動作デモ](app/static/calculator_demo.gif)

本プロジェクトは、Pythonベースの軽量Webフレームワークである **FastAPI** と、フロントエンドの動的描画を容易にする **HTMX** を用いて開発されたシンプルなWeb電卓アプリケーションです。ブラウザ上で動作する対話的なUIを提供するだけでなく、外部プログラムから利用可能なJSON APIとしての機能も備えています。

## 目次
- [プロジェクトの概要と主な機能](#プロジェクトの概要と主な機能)
- [フォルダ構成とファイル一覧](#フォルダ構成とファイル一覧)
- [ローカル環境での実行方法（クイックスタート）](#ローカル環境での実行方法クイックスタート)
- [API 仕様](#api-仕様)
- [テストとカバレッジ（計測・実行方法）](#テストとカバレッジ計測実行方法)
- [Docker コンテナでの実行（デプロイ）](#docker-コンテナでの実行デプロイ)
- [ライセンス](#ライセンス)

## プロジェクトの概要と主な機能
- **HTMXによるSPAライクなUI**：ページ遷移を伴わず、非同期通信によってDOMの一部のみを更新する快適なユーザー体験を実現しています。
- **RESTful APIの提供**：バックエンドに `/api/calculate` エンドポイントを実装しており、別アプリケーションからのJSONベースの計算リクエストに対応可能です。
- **安全な式評価ロジック**：`eval`の脆弱性を回避するため、抽象構文木（AST）を利用したサンドボックス型の計算ロジックを独自実装しています。
- **堅牢なテストとCI/CD**：`pytest` や `Playwright` を用いた自動テスト網と GitHub Actions による自動検証（CI）が構築されています。

## フォルダ構成とファイル一覧

以下は本プロジェクトの主要なファイルとディレクトリ構成です。

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions の CI/CD 設定ファイル
├── app/
│   ├── main.py                # FastAPI アプリケーションのエントリポイント
│   ├── routers/               # （将来の拡張用）ルーティングディレクトリ
│   ├── schemas/               # （将来の拡張用）データスキーマ定義
│   ├── services/
│   │   ├── calculator.py      # ASTを用いた安全な計算ロジック（コアロジック）
│   │   └── convert.py         # 補助処理用モジュール
│   ├── static/                # CSS, JS, 画像などの静的ファイル
│   │   └── htmx.min.js        # HTMXライブラリ
│   └── templates/             # Jinja2 テンプレート
│       ├── index.html         # 電卓のメインUI画面
│       └── result.html        # HTMXで部分更新される計算結果用パーツ
├── docs/
│   └── openapi.yaml           # API仕様書（OpenAPIフォーマット）
├── tests/
│   ├── test_calculator.py     # 計算ロジックおよびAPIのユニットテスト
│   └── test_ui.py             # Playwright を用いた E2E（ブラウザ）テスト
├── Dockerfile                 # 本番・デプロイ用コンテナイメージ定義
├── pyproject.toml             # uv を用いたプロジェクト設定と依存関係（Linter等の設定含む）
├── pytest.ini                 # pytest の基本設定（Playwright無効化等の保護設定）
├── run.bat / run.sh           # アプリケーションをDockerで起動するためのスクリプト
├── test_ui.bat / test_ui.sh   # ローカルで E2E テストを安全に実行するためのスクリプト
└── README.md                  # 本ドキュメント
```

## ローカル環境での実行方法（クイックスタート）
本アプリケーションをローカル環境で動作させる手順は以下の通りです。パッケージマネージャーとして `uv` を使用します。

```bash
# 1. リポジトリのクローンとディレクトリへの移動
git clone <リポジトリURL>
cd calculator

# 2. 依存パッケージのインストール（uvを利用）
uv sync

# 3. 開発用サーバーの起動
uv run uvicorn app.main:app --reload --port 8000
```
サーバーが起動したら、ブラウザで `http://localhost:8000` にアクセスすると、電卓のUI画面が表示されます。

## API 仕様
他のプログラムやクライアントから計算処理を呼び出すためのAPIエンドポイントについて説明します。

### POST `/api/calculate`
- **リクエスト形式**（`application/json`）: `{ "expression": "<算術式>" }`
- **レスポンス形式**:
  - `200 OK` (正常終了) – `{ "result": <数値>, "expression": "..." }`
  - `400 Bad Request` (エラー) – `{ "error": "<エラー詳細>", "expression": "..." }` （例: ゼロ除算や不正な式の入力時）

### OpenAPI ドキュメント（Swagger UI / ReDoc）
ローカルサーバー起動中に以下のURLにアクセスすることで、ブラウザから直接APIの仕様確認およびテスト実行が可能です。
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## テストとカバレッジ（計測・実行方法）
本プロジェクトは、`pytest`、`coverage`（`pytest-cov`）および `Playwright` を用いた品質保証が行われています。

### 1. ユニットテストの実行
ローカル環境では、APIや内部ロジックに対するユニットテストを以下のコマンドで実行できます。
（※ローカル環境保護のため、デフォルトでブラウザを用いたE2Eテストはスキップされます）

```bash
uv run pytest
```

### 2. E2E（ブラウザ）テストの実行
HTMXの動作など、実際のブラウザ挙動を検証する E2E テストは、環境依存（DLLエラー等）を防ぐため **Docker環境での実行** を推奨しています。専用のスクリプトを使用してください。

- **Windows**: `test_ui.bat` を実行
- **macOS / Linux**: `bash test_ui.sh` を実行

### 3. テストカバレッジの計測方法
コードカバレッジ（テスト網羅率）を計測して結果を出力するには、以下のコマンドを実行します。

```bash
# pytest-cov を利用したカバレッジ計測とコンソール出力
uv run pytest --cov=app --cov-report=term-missing
```

**カバレッジ計測結果（コアロジックは100%を維持）:**
```text
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
app\__init__.py                    0      0   100%
app\main.py                       43      1    98%   66
app\routers\__init__.py            0      0   100%
app\schemas\__init__.py            0      0   100%
app\services\__init__.py           0      0   100%
app\services\calculator.py        18      0   100%
app\services\convert.py           30     24    20%   8-54
------------------------------------------------------------
TOTAL                             91     25    73%
```
*(※ `app.main` および `app.services.calculator` などの中核ロジックは実質100%近いカバレッジを維持しています。)*

## Docker コンテナでの実行（デプロイ）
Dockerを利用して、ローカルの依存環境に影響されることなくアプリケーションを実行できます。

**起動スクリプトを使用する方法:**
プラットフォームに応じたスクリプトを実行することで、イメージのビルドとコンテナの起動を自動で行います。
- **Windows**: `run.bat` を実行
- **macOS / Linux**: `bash run.sh` を実行

**コマンドを手動で実行する方法:**
```bash
# コンテナイメージのビルド
docker build -t calculator-app .
# コンテナのバックグラウンド起動とポートマッピング
docker run --rm -p 8000:8000 calculator-app
```
起動後は、同様に `http://localhost:8000` にアクセスしてアプリケーションを利用できます。

## ライセンス
本プロジェクトは **MIT ライセンス** の下で公開されています。詳細についてはリポジトリ内の `LICENSE` ファイルを参照してください。誰でも自由に使用、改変、再配布することが可能です。
