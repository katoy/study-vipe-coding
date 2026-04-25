クイックスタート

ローカル開発:
1. 依存を同期
   uv sync
2. 開発サーバー起動
   uv run uvicorn app.main:app --reload --port 8000
3. ブラウザで http://localhost:8000 を開く

API 例:

- JSON API（デフォルト: 数値を返す）

```bash
curl -s -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression":"3/2"}'
```

- 小数を分数で返す（show_fraction）

```bash
curl -s -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression":"3/2","show_fraction":true}'
# -> { "result": "1 1/2", "expression": "3/2" }
```

- 循環小数表記: 結果の循環小数は波括弧で表現します（例: 1/3 -> "0.{3}"）。入力でも `0.{3}` のように記述できます。

OpenAPI 定義: docs/openapi.yaml

プログラムからの利用例:

- Calculator クラス直接利用

```python
from app.services.calculator import Calculator
calc = Calculator()
res = calc.safe_eval("3/2")
```

- 実行中のアプリケーションで共有されるインスタンスを利用 (app.main.calc)

```python
from app.main import calc
res = calc.safe_eval("3/2")
```

テスト:
- 単体テスト: uv run pytest
- E2E (Playwright): Docker 環境での実行を推奨（スクリプト: test_ui.bat / test_ui.sh）。

Docker:
- ビルド: docker build -t calculator-app .
- 実行: docker run --rm -p 8000:8000 calculator-app

環境変数の主な説明:
- ALLOW_ORIGINS: CORS許可オリジン（カンマ区切り）。デフォルト: http://localhost:8000
- ALLOW_POW: べき乗を有効にする (1/true)。デフォルトは無効（安全ガードあり）。
- RATE_LIMIT_PER_MIN: 1分あたりのAPI上限（デフォルト 60）。単一プロセス向けの簡易実装です。

