API リファレンス

- POST /api/calculate
  - リクエスト JSON: { "expression": "<算術式>" }
  - 正常: 200 { "result": <数値>, "expression": "..." }
  - エラー: 400 { "error": "<詳細>", "expression": "..." }

OpenAPI 定義は docs/openapi.yaml を参照
