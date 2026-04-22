# コードレビュー結果（総合・修正指示）

参照: review-001.md, review-002.md

目的: 過去レビューを踏まえ、リポジトリ内の主要ファイルを再レビューし、優先度付きの修正項目と具体的な修正案をまとめる。

---

## 要約（上位優先事項）

1. app/main.py の Jinja2 TemplateResponse 呼び出し順に誤りがあり、テンプレート描画が失敗します。緊急修正。
2. 例外処理が広範すぎて内部エラーを隠蔽しています。ユーザ入力由来の例外のみ丁寧に捕捉し、それ以外はサーバーエラー(500)としてログ出力すること。
3. CORS が allow_origins=["*"] になっています。本番では特定オリジンに制限してください。
4. calculator.safe_eval: 長さ制限はあるが、巨大ネストや再帰系の攻撃（RecursionError）対策を強化する。べき乗(ast.Pow) や単項プラス(ast.UAdd) の扱いについて明記。
5. README.md と実ファイル構成・CI 設定に齟齬があるため、ドキュメントを実態に合わせて更新する。

---

## ファイルごとの指摘と修正案

### app/main.py (P0)
- 問題点:
  - templates.TemplateResponse の呼び出しが "TemplateResponse(request, \"index.html\", {...})" など誤った順序で使用されている。
  - except Exception: による過剰な例外捕捉。
- 修正案:
  - templates.TemplateResponse("index.html", {"request": request, ...}) の形に統一。
  - 例外は ZeroDivisionError, SyntaxError, ValueError 等に限定して捕捉し、その他は logger.error(..., exc_info=True) を残して 500 を返す。
  - ロギングを充実させスタックトレースを出力。
  - CORS 設定を環境変数で制御（デフォルトは厳格）する。

### app/services/calculator.py (P1)
- 問題点:
  - 入力長制限(100)はあるが、巨大ネストによる RecursionError を明確に扱っていない。
  - 必要なら ast.Pow を許可し、許可される演算子を明示的に列挙すること。
- 修正案:
  - ast.parse の直後に最大ノード数や最大深さをチェック（再帰深さの測定/拒否）。
  - RecursionError を捕捉して ValueError に変換するか、API層で 400 を返す。
  - ユニットテストで +5 や ** 演算子、境界長のケースを追加。

### Dockerfile (P2)
- 良好: 非 root ユーザ作成、pyproject を利用した依存インストール。
- 推奨: ビルドキャッシュ無効化やロックファイル（uv.lock）を COPY して再現性を高める。イメージ最小化のため不要ファイルを .dockerignore に追加。

### README.md (P1)
- 問題点: 実ファイル構成や CI、コマンド例に実態との齟齬あり。
- 修正案: 実ファイル名/パス、起動コマンド、テスト手順、E2E 実行方法を正確に合わせる。

---

## テスト・CI に関する提案

- tests に Playwright E2E が含まれている場合、CI では Docker 上で実行するワークフローを用意する（GitHub Actions）。
- pytest のテストカバレッジを保ちながら、例外処理の変化に対する回帰テストを追加。

---

## 次のアクション（推奨順）
1. app/main.py の TemplateResponse 呼び出し修正と例外処理の見直し（即時）。
2. calculator.safe_eval の堅牢化（再帰深さチェック、追加ユニットテスト）。
3. README の実態合わせと Dockerfile の小修正。
4. CORS 設定を環境依存に変更し、CI を追加（任意）。

---

上記を実施するパッチを作成可能です。どの項目から着手しますか？
