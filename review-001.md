# コードレビュー結果 (review-001)

全体のソースコードに対して、実運用（プロダクション）を想定した厳格なコードレビューを実施しました。主にアーキテクチャ、パフォーマンス、セキュリティ、Dockerのベストプラクティス、ドキュメントの整合性の観点から、AIやシニアエンジニアが指摘するであろうポイントをまとめています。

## 1. パフォーマンス・アーキテクチャの課題

### ① テンプレートの毎回の読み込みとパース (`app/main.py`)
- **指摘事項**: 現在の `render_template` は、リクエストが来るたびにファイルの読み込み（I/O）と Jinja2 の構文解析（`Template(...)`）を行っています。アクセスが少ないうちは問題ありませんが、アクセスが集中すると重大なボトルネックになります。
- **改善案**: FastAPI に標準で備わっている `Jinja2Templates` を使用するべきです。これにより自動でキャッシュが効き、パフォーマンスが劇的に向上します。
  ```python
  from fastapi.templating import Jinja2Templates
  templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
  
  @app.get("/", response_class=HTMLResponse)
  async def index(request: Request):
      return templates.TemplateResponse("index.html", {"request": request, "result": None, "expression": ""})
  ```

### ② APIのリクエスト形式が JSON ではなく Form (`app/main.py`)
- **指摘事項**: `/api/calculate` が `Form(...)` でデータを受け取っています。Webフロント（HTMX）からの送信はForm形式が便利ですが、純粋な JSON API として他システムから呼ばれることを想定する場合、`application/json` を受け付けるべきです。
- **改善案**: Pydantic モデル（`BaseModel`）を定義し、JSON で受け取るAPI設計にすると、FastAPI の型バリデーションの恩恵をフルに受けられます。

## 2. セキュリティと堅牢性

### ① 抽象構文木 (AST) 評価の制限 (`app/services/calculator.py`)
- **指摘事項**: `safe_eval` は RCE（任意コード実行）を防ぐ良いアプローチですが、**単項プラス演算子 (`+5` など)** が未定義のため、`+5 + 3` のような式が `ValueError("不正な式")` になってしまいます。また、べき乗 (`**`) もサポートされていません。
- **改善案**: `ast.UAdd` を許可リストに追加すると、よりユーザーにとって自然な電卓になります。
- **指摘事項 (リソース枯渇攻撃対策)**: 巨大な数式（例: 100万回ネストされたカッコ）が送られた場合の再帰エラー (`RecursionError`) や CPU枯渇（ReDoS等に似た攻撃）を防ぐ防御がありません。
- **改善案**: 入力文字列の長さ上限（例: 100文字まで）を設けるべきです。

## 3. Docker と再現性の課題

### ① Dockerfile の依存関係インストールがハードコードされている (`Dockerfile`)
- **指摘事項**: `Dockerfile` 内で `RUN pip install fastapi uvicorn ...` と直接パッケージを指定してインストールしています。プロジェクトには `pyproject.toml` や `uv` があるため、これらを活用できていません。
- **改善案**: パッケージのバージョン違いによるバグを防ぐ（ビルドの再現性を担保する）ため、`pyproject.toml` を使って依存関係をインストールするべきです。
  ```dockerfile
  RUN pip install uv
  COPY pyproject.toml .
  RUN uv pip install --system .
  ```

### ② コンテナの root 実行権限 (`Dockerfile`)
- **指摘事項**: 現在の Docker コンテナはデフォルトの `root` ユーザーで実行されます。これはコンテナセキュリティの観点から推奨されません。
- **改善案**: 最後に一般ユーザー（`appuser`など）を作成し、`USER appuser` に切り替えてからプロセスを起動するようにします。

## 4. ドキュメント (README.md) の更新漏れ

ディレクトリ構成をリファクタリング（`app/` 構成への変更）した影響で、`README.md` の記述と現在の実態にズレが生じています。
- **起動コマンドのズレ**: `uv run uvicorn app:app` → **`uv run uvicorn app.main:app`** が正しいコマンドです。
- **カバレッジのズレ**: 結果の表記が `app.py` などのままになっていますが、現在は `app/main.py` や `app/services/calculator.py` です。
- **画像パスのズレ**: `static/calculator_demo.gif` は `app/static/calculator_demo.gif` に移動したため、相対パスがズレています。
