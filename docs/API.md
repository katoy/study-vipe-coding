API リファレンス

- POST /api/calculate
  - リクエスト JSON: { "expression": "<算術式>", "show_fraction": <bool, optional> }
  - 正常: 200 { "result": <数値 または 文字列（例: "1 1/2" や "0.{3}"）>, "expression": "..." }
  - エラー: 400 { "error": "<詳細>", "expression": "..." }
  - 内部エラー: 500 { "error": "..." }

- POST /calculate (HTML フォーム、HTMX 運用)
  - フォームデータ: expression (必須), show_fraction (オプション, boolean 相当)
  - レスポンス: result を含む部分 HTML（templates/result.html）

OpenAPI 定義は docs/openapi.yaml を参照

プログラム的利用:

- ライブラリとして呼び出す場合は `Calculator` クラスを利用できます。

```python
from app.services.calculator import Calculator
calc = Calculator()
result = calc.safe_eval("1/3")
```

- アプリ実行中の共有インスタンスを使う場合は `from app.main import calc` でアクセスできます（テストではこのインスタンスをモックすることが推奨されます）。
