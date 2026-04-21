# 電卓 Web アプリケーション

FastAPI をベースにしたシンプルな電卓アプリです。基本的な算術演算をサポートし、HTML UI と JSON API の両方を提供します。

## 主な機能
- **HTMX** を利用したインタラクティブな UI（ページ遷移なしで計算結果を表示）
- プログラムから利用できる **JSON API**（`/api/calculate`）
- 安全な式評価を実装したサンドボックス型計算ロジック
- **pytest** と **coverage** によるテストカバレッジ 100%（全 17 テスト）
- Dockerfile が同梱されており、コンテナでのデプロイが容易

## クイックスタート
```bash
# リポジトリをクローン（まだの場合）
git clone <リポジトリURL>
cd calculator

# 依存パッケージをインストール（uv が既にセットアップ済み）
uv sync   # fastapi, uvicorn, jinja2, httpx, coverage などがインストールされます

# 開発サーバーを起動
uv run uvicorn app:app --reload --port 8000
```
ブラウザで `http://localhost:8000` にアクセスすると電卓 UI が表示されます。

## API 仕様
### POST `/api/calculate`
- **リクエスト**（form-encoded）: `{ "expression": "<算術式>" }`
- **レスポンス**:
  - `200 OK` – `{ "result": <数値>, "expression": "..." }`
  - `400 Bad Request` – `{ "error": "<エラーメッセージ>", "expression": "..." }`

## テストとカバレッジの実行
```bash
# テストを実行
uv run coverage run -m pytest
# カバレッジレポートを表示
uv run coverage report -m
```
すべてのテストが成功し、カバレッジはほぼ100%になります（20 test passed）。

**カバレッジ実行結果例:**
```text
Name                       Stmts   Miss  Cover
----------------------------------------------
app.py                        39      0   100%
calculator.py                 17      0   100%
tests\test_calculator.py      83      2    98%
----------------------------------------------
TOTAL                        139      2    99%
```

## Docker でのデプロイ
同梱の `Dockerfile` を使用してコンテナイメージをビルドし、実行できます。
```bash
docker build -t calculator .
docker run -p 8000:8000 calculator
```
コンテナ起動後も `http://localhost:8000` で利用可能です。

## ライセンス
MIT ライセンス（`LICENSE` ファイル参照）。
