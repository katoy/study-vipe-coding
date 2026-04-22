# Webベース電卓アプリケーション 構築プロンプト

AIエージェント（Antigravity等）に渡して、本プロジェクトと全く同じ機能・構成のアプリケーションをゼロから構築させるためのプロンプト例です。

---

## プロンプト（指示書）

あなたは優秀なフルスタックエンジニアです。以下の要件に従って、セキュアでテスト網羅率の高い「Webベースの電卓アプリケーション」をゼロから構築してください。

### 1. 技術スタック
- **バックエンド**: FastAPI, Python 3.12+
- **フロントエンド**: HTML + vanilla CSS + HTMX (JavaScriptは最小限)
- **パッケージ管理**: `uv` (pyproject.tomlベース)
- **テスト**: `pytest`, `pytest-cov`, `pytest-playwright`
- **静的解析**: `Ruff` (Formatter/Linter), `mypy` (型チェック)

### 2. ディレクトリ構成
以下の `src` ライクなクリーンアーキテクチャ構成を採用してください。
```text
.
├── .github/workflows/ci.yml
├── app/
│   ├── main.py (FastAPIエントリポイント, CORS設定, Jinja2Templates)
│   ├── services/
│   │   └── calculator.py (計算のコアロジック)
│   ├── static/
│   └── templates/
│       ├── index.html (電卓UI)
│       └── result.html (HTMX用部分テンプレート)
├── tests/
│   ├── test_calculator.py (ロジック・APIのユニットテスト)
│   └── test_ui.py (Playwrightを用いたE2Eテスト)
├── Dockerfile (非root実行, uvによるインストール)
├── pyproject.toml
└── README.md
```

### 3. コア機能要件
1. **電卓UI**:
   - `index.html` に、0-9の数字、四則演算（+ - * /）、AC（クリア）、=（計算）ボタンを配置する。
   - デザインはモダンで直感的なもの（例: 角丸、シャドウ、ボタンのホバーエフェクト）にする。
   - 計算実行はフォーム送信とするが、**HTMX** を用いてページ全体をリロードせず、結果部分（`result.html`）のみを非同期でDOM更新する。
2. **安全な計算ロジック (`app/services/calculator.py`)**:
   - セキュリティのため、標準の `eval()` は絶対に**使用しない**こと。
   - `ast` (抽象構文木) モジュールを利用して、安全な四則演算と単項プラス・マイナスのみを許可する独自の評価関数を作成する。
   - リソース枯渇攻撃を防ぐため、計算式の文字列長は100文字までに制限する。
3. **API エンドポイント (`app/main.py`)**:
   - `GET /` : UIを提供するHTMLを返す。
   - `POST /calculate` : HTMXからのFormデータ（算術式）を受け取り、計算結果をHTMLパーツ（`result.html`）として返す。
   - `POST /api/calculate` : 外部連携用API。Pydanticモデルを用いたJSONリクエスト(`{"expression": "..."}`)を受け取り、JSONレスポンスを返す。
4. **エラーハンドリングとロギング**:
   - ゼロ除算、構文エラーなどは適切にキャッチし、ユーザーには分かりやすいエラーメッセージを返すこと。
   - バックエンド側には `logging` を用いて警告やスタックトレースを記録すること。

### 4. テストと品質保証要件
- ユニットテスト (`test_calculator.py`) でコアロジックと両APIエンドポイントを検証し、**カバレッジを100%** に近づけること。
- Playwright を用いたE2Eテスト (`test_ui.py`) で、ブラウザ上でのボタンクリックと計算結果の表示を検証すること。ローカル保護のため、`pytest.ini` ではPlaywrightをデフォルトで無効化し、必要な時だけ実行できるようにする。
- `Ruff` と `mypy` による静的解析が通るように型ヒントを完備すること。

### 5. デプロイとCI/CD
- **Dockerfile**:
  - `python:3.12-slim` などをベースにする。
  - `uv` をインストールして `pyproject.toml` からシステムワイドに依存関係を解決する。
  - セキュリティベストプラクティスに従い、**非rootユーザー (`appuser`)** を作成して実行する。
- **GitHub Actions (`ci.yml`)**:
  - push / PR 時に、`uv` のセットアップ、`ruff`, `mypy`、`pytest` (Playwrightテストも有効化して実行)、および `docker build` の検証がすべて自動で走るワークフローを作成すること。

---
上記を満たすアプリケーションのコード、設定ファイル群、および起動用スクリプトを一式生成してください。
