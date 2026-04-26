# プロジェクト全体レビュー: FastAPI 電卓アプリケーション

**レビュー日:** 2026-04-26
**レビュアー:** Claude Opus 4.6
**対象ブランチ:** refactor/initial
**Python コード行数:** 約1,100行 / テスト68件 / カバレッジ93%

## 総合評価: B+ (良好、改善余地あり)

テスト65件全通過、カバレッジ93%、lint/型チェック全クリアという安定した基盤を持つ。セキュリティ意識（AST評価、入力長制限、レートリミット）も高い。一方で、設計・運用面にいくつかの課題がある。

---

## 1. セキュリティ (重要度: 高)

### 1-1. f-string によるログインジェクション — `main.py:99,105,111`

```python
logger.warning(f"Division by zero: {expression}")
```

ユーザー入力を `f-string` でそのままログに書き込んでいる。攻撃者が改行や ANSI エスケープシーケンスを含む式を送信した場合、ログ偽装（log injection）が可能。

**推奨:** `logger.warning("Division by zero: %s", expression)` のように `%s` プレースホルダを使用する。

### 1-2. レートリミットのクライアント識別 — `main.py:59-61`

```python
client_host = "unknown"
if request.client and request.client.host:
    client_host = request.client.host
```

リバースプロキシ背後では全リクエストが同一IPとなり、正規ユーザーが巻き込みでブロックされる。逆に、`X-Forwarded-For` をパースしないためプロキシなしでは機能するが、本番想定が不明瞭。

**推奨:** 本番環境で使う場合は `X-Forwarded-For` のパース（信頼プロキシリストと組み合わせ）または外部ミドルウェア（nginx等）でのレート制限を検討する。

### 1-3. CORS の `allow_methods=["*"]` — `main.py:31`

全HTTPメソッドを許可している。電卓アプリなら `GET, POST` のみで十分。不要なメソッドを開放するのは攻撃面の拡大。

### 1-4. htmx の CDN 読み込み — `index.html:149`

```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
```

`/static/htmx.min.js` がローカルに存在するのに CDN から読み込んでいる。CDN 改ざんリスクがあり、SRI（Subresource Integrity）ハッシュも付与されていない。

**推奨:** ローカルの `/static/htmx.min.js` を使うか、最低限 `integrity` 属性を追加する。

---

## 2. バグ / 論理的問題 (重要度: 高)

### 2-1. `ALLOW_POW` が毎回 `os.getenv` で評価される — `calculator.py` の `safe_eval`

```python
allow_pow = os.getenv("ALLOW_POW", "0").lower() in ("1", "true", "yes")
```

`safe_eval` が呼ばれるたびに環境変数を再読み込みしている。これはクラスのコンストラクタで設定すべき値であり、呼び出しごとに変わりうるのは設計上の不整合。テストでは `monkeypatch.setenv` + 新インスタンス生成で対応しているが、本番の `calc` インスタンスは起動時に1回だけ生成されるため、途中で環境変数を変えても反映されない（`_OPS` は `__init__` で固定済み）のに `safe_eval` 内で再チェックしている矛盾がある。

**推奨:** `__init__` で `allow_pow` を確定し、`_OPS` にその時点で `ast.Pow` を含めるか否かを決定する。

### 2-2. `_safe_pow` が `Fraction` を受け付けない — `calculator.py:37`

```python
def _safe_pow(self, left: int | float, right: int | float) -> int | float:
```

`_eval_node` は `Fraction` を返しうる（除算時）が、`_safe_pow` のバリデーションは `isinstance(right, int)` のみ。`Fraction(3, 1)` は `int` ではないため、`Fraction(3,1) ** 2` のような正当な式が拒否される。

### 2-3. `test_rate_limit.py` での `importlib.reload` の副作用

モジュール再読み込みにより、グローバルな `app` オブジェクトが置換される。他のテストファイルが `from app.main import app` でキャプチャした参照に影響を与える可能性がある。テスト実行順序によってはフレイキーテストの原因になりうる。

---

## 3. 設計 / アーキテクチャ (重要度: 中)

### 3-1. `convert.py` は未使用のスクリプトファイル

`app/services/convert.py` は `Pillow` を使った画像変換スクリプトで、アプリケーションのどこからもインポートされていない。`coverage.run.omit` で除外もされているが、`app/services/` に置くのは紛らわしい。

**推奨:** `scripts/` ディレクトリへ移動するか、不要なら削除。

### 3-2. `CalculatorClass = Calculator` — `calculator.py` 最終行

目的が不明なエイリアス。使用箇所もない。不要なコードは削除すべき。

### 3-3. 空の `__init__.py` が多い

`app/routers/__init__.py`, `app/schemas/__init__.py` — 対応するモジュールが存在しない空パッケージ。将来の拡張を見越した骨格だが、現時点では YAGNI（You Ain't Gonna Need It）。

### 3-4. `conftest.py` のデバッグログ

```python
print("PYTEST_CONFTEMP: sys.path length:", len(sys.path))
```

デバッグ用の `print` 文が残っている。テスト出力を汚染し、CI ログの視認性を下げる。

### 3-5. レートリミットの `threading.Lock` はASGIでは不十分

FastAPIは `asyncio` ベースだが、レートリミットに `threading.Lock` を使っている。Uvicorn のワーカー数が1であれば問題ないが、マルチワーカー (`--workers N`) 構成では各ワーカーが独立した `_rate_store` を持つため、レートリミットが正しく機能しない。

---

## 4. CI / DevOps (重要度: 中)

### 4-1. CI ワークフローが2つ存在し役割が重複

- `ci.yml`: push時にlint+型チェック+Docker+E2E
- `test.yml`: PR時にpytest+カバレッジ

`ci.yml` に **テスト実行ステップがない**。lint と E2E はあるが、ユニットテストが CI パイプラインから漏れている。`test.yml` は PR のみで push 時には走らない。

**推奨:** `ci.yml` にユニットテスト＋カバレッジのステップを追加するか、2つのワークフローを統合する。

### 4-2. `test.yml` が `pip` を直接使用

```yaml
python -m pip install -U pip
pip install pytest pytest-cov ...
```

`pyproject.toml` で `uv` を使っているのに、CI の片方は `pip` で手動インストール。依存バージョンがロックファイルと乖離するリスクがある。

### 4-3. Dockerfile の `as base` は非推奨構文

```dockerfile
FROM python:3.12-slim as base
```

BuildKit では `AS`（大文字）が標準。動作はするが、lint ツールが警告を出す。

### 4-4. `compose.yaml` の healthcheck

```yaml
test: ["CMD", "curl", "-f", "http://localhost:8000/" , "||", "exit", "1"]
```

`python:3.12-slim` イメージには `curl` が入っていない。ヘルスチェックは常に失敗する。

**推奨:** `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"` を使う。

### 4-5. `.gitignore` に不足

`coverage.xml`, `.ruff_cache/`, `.DS_Store`, `*.egg-info/`, `tests/e2e_server.log` がトラッキングされている。これらはリポジトリに含めるべきではない。

---

## 5. コード品質 / スタイル (重要度: 低〜中)

### 5-1. `result.html` の `fraction_parts` 未定義リスク

エラー時のコンテキストに `fraction_parts` が含まれないが、テンプレート側で `{% if fraction_parts ... %}` がある。Jinja2 は未定義変数で `UndefinedError` を投げる可能性があるが、`is_error` ブランチで回避されている。ただし、テンプレートの `undefined` 設定が明示されていないため、脆弱な前提。

**推奨:** テンプレートで `fraction_parts is defined and fraction_parts` とするか、全コンテキストで `fraction_parts` を渡す。

### 5-2. 型注釈の不整合

- `_safe_pow` の引数型は `int | float` だが、`Number = Union[int, float, Fraction]` が定義済み。`Number` を使うべき。
- `format_result` の戻り値型 `int | float | str` は `Number | str` と書ける。

### 5-3. `safe_eval` の入力長チェックが二段構え

100文字超で一度チェックし、特殊記法がなければ拒否。その後20,000文字で絶対上限チェック。ロジックは正しいが、定数がコード内にハードコードされており（`100` は `max_expr_length` だが `20000` は直書き）、一貫性がない。

### 5-4. `index.html` の `--muted-text` CSS変数未定義

```html
<div style="...color:var(--muted-text)...">循環小数は...
```

定義されているのは `--muted` であり `--muted-text` ではない。このテキストは透明（フォールバック無し）で表示されない可能性がある。

**これはバグ:** `--muted` に修正すべき。

---

## 6. テスト (重要度: 中)

### 6-1. テストの重複

`test_calculator_safety.py` と `test_services_calculator.py` で `pow` テストが重複。`test_pow.py` でも同様のテストがある。3ファイルに分散した同一テストは保守コストを上げる。

### 6-2. E2E テストのポート固定 — `test_ui.py:39`

```python
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, ...)
```

ポート8000がハードコード。ローカルで開発サーバーが動いている場合にポート競合でテストが失敗する。

**推奨:** `port=0` で空きポートを取得し、動的に使う。

### 6-3. カバレッジ未到達部分

`calculator.py` のカバレッジ91%。未到達の9%は `float_to_repeating_decimal` の一部エッジケースと `format_result` の一部パス。重要なビジネスロジックなのでカバーすべき。

---

## 7. 即座に修正すべき項目（優先順位順）

| # | 問題 | 重要度 | 影響 |
|---|------|--------|------|
| 1 | CSS変数 `--muted-text` 未定義（UIバグ） | **高** | ヒントテキストが見えない |
| 2 | htmx CDN → ローカル切替 | **高** | サプライチェーンリスク |
| 3 | ログインジェクション対策 | **高** | セキュリティ |
| 4 | `compose.yaml` の curl ヘルスチェック | **中** | Docker運用時に必ず失敗 |
| 5 | `.gitignore` 不足 | **中** | 不要ファイルがリポジトリに混入 |
| 6 | CI にユニットテストステップ欠落 | **中** | テストなしでマージ可能 |
| 7 | `ALLOW_POW` の設計矛盾 | **中** | 環境変数変更が予測不能な動作に |
| 8 | `conftest.py` のデバッグprint除去 | **低** | ログ汚染 |

---

## 8. 良い点（評価すべき実装）

- **AST ベースの安全な式評価**: `eval()` を使わず `ast.parse` + ホワイトリスト演算子で堅牢
- **べき乗の底・指数の上限制限**: DoS 防止として適切
- **循環小数の入出力対応**: `0.{3}` 記法の実装は教育用途として優れている
- **帯分数変換・分数プレビュー**: UX上の配慮
- **レートリミットの期限切れエントリ掃除**: メモリリーク対策済み
- **アクセシビリティ**: `aria-label`, `role="status"`, `aria-live="polite"` の適切な使用
- **テストカバレッジ93%**: 十分な水準
- **Docker マルチステージビルド**: 本番イメージとCIイメージの分離
