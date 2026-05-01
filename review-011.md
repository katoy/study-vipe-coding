# コード全体レビュー (review-11)

対象ブランチ: `fix/cloud-run-port`
レビュー日: 2026-04-30
対象範囲: `app/`, `tests/`, `scripts/`, `Dockerfile`, `compose.yaml`, `setup_cloud_run.sh`, `.github/workflows/ci.yml`, `pyproject.toml`

---

## 1. 総評

電卓 Web アプリは、FastAPI + HTMX + Jinja2 のシンプルかつ堅牢な構成で、`Fraction` を中核に据えた **正確算術 (浮動小数点誤差ゼロ)** が大きな特長です。AST ベースの安全な式評価、レート制限、CORS 設定、Cloud Run デプロイまで広く整備されており、テストカバレッジも高水準。一方で、レート制限のスケーラビリティ、循環小数前処理の正規表現の重複、ビュー層の責務肥大、Docker イメージサイズなど、「製品化に向けて」の改善余地はあります。

総合評価: **B+ (良好。製品リリース手前)**

---

## 2. 良い点 (Strengths)

### 2.1 セキュア & 安全な式評価 (`app/services/calculator.py`)

- `eval` を使わず Python AST を `_eval_node` で再帰的に評価。許可した `ast.Add/Sub/Mult/Div/Mod/USub/UAdd` のみを処理し、`__import__` 等のインジェクションを完全に排除。
- 複雑度ガード (`_check_complexity`): ノード数 (max 2000) と深さ (max 60) を制限。
- 長さガード: 二段階制限 (`max_expr_length=100` と `MAX_EXPR_LENGTH_ABSOLUTE=20000`)。
- べき乗 (`ast.Pow`) は環境変数 `ALLOW_POW` で opt-in。さらに `_safe_pow` で `|exp| <= 20`, `|base| <= 10^6` を強制。
- `RecursionError` を `ValueError` に変換し、サービス層で内部化。
- テスト `test_injection_blocked` で代表的なペイロードを網羅。

### 2.2 正確算術 (浮動小数点誤差ゼロ)

- `_eval_node` の `ast.Constant` 処理で `float` を `Fraction(str(...))` に変換し、`0.1 + 0.2 == Fraction(3, 10)` を実現。
- 除算は常に `Fraction` を返し、自然数結果は `int` に正規化。
- 循環小数の波括弧記法 `0.1{6}` を専用前処理で `Fraction` 化。`1/3` → `0.{3}` → 再入力可能、というラウンドトリップを成立させている (`test_safe_eval_repeating_decimal_display_can_be_reused`)。
- 帯分数入力 `2 2/3` も同様にサポート。

### 2.3 テスト充実度

- ユニット (`tests/test_services_calculator.py`)、API (`tests/test_calculator.py`)、UI/E2E (`tests/test_ui.py`)、内部分岐 (`tests/test_calculator_internal_checks.py`)、レート制限 (`tests/test_rate_limit.py`)、CORS (`tests/test_cors.py`)、エラーハンドリング (`tests/test_api_error_handling.py`) と層別に整理。
- `test_force_execute_delete_line_in_main` のようにカバレッジ充足のために巧妙な exec を使うなど、99% ブランチカバレッジを意識した作り。
- E2E では Playwright で実 UI を駆動。
- 注入攻撃・深いネスト・式長すぎ・ゼロ除算など、エッジケースを網羅。

### 2.4 アーキテクチャ

- 責務分離: ビュー (`app/main.py`) ⇔ ドメイン (`app/services/calculator.py`) ⇔ テンプレート (`app/templates/*.html`)。
- HTMX による部分的 UI 更新と OOB swap で、ページ全体リロードなしの結果反映。
- `Calculator` クラスが純粋ロジックで、依存注入が容易 (`monkeypatch` テストが豊富)。

### 2.5 開発者体験

- Ruff + mypy strict + pre-commit + pre-push の品質ゲート。
- `pyproject.toml` で dev グループを切り分け。
- `setup_cloud_run.sh` で GCP の API 有効化、Artifact Registry 作成、Cloud Build、Cloud Run デプロイをワンスクリプト化。
- Dockerfile はマルチステージ (`base` / `ci` / `final`) で本番イメージから dev tool を除外、非 root 実行 (`appuser`)。
- CI に format / lint / type / unit / docker build / e2e を組み込み。

---

## 3. 改善すべき点 (Issues / Risks)

### 3.1 [中] レート制限のスケーラビリティ・正確性

**ファイル**: `app/main.py:41-70`

- ストアがプロセス内 `dict` (`_rate_store`)。Cloud Run では複数インスタンスが並走するため、IP あたり真の上限が `RATE_LIMIT_PER_MIN × インスタンス数` になる。
- 期限切れエントリの掃除は「新規ウィンドウ作成時の同一クライアント要求」契機でしか走らないため、未再訪 IP のエントリが滞留する可能性。攻撃者が大量の偽 IP を投げると `_rate_store` が肥大化し続ける (DoS)。
- `request.client.host` は X-Forwarded-For を見ていないため、Cloud Run やリバースプロキシ越しでは全要求が同一 IP (フロント IP) と認識されうる。

**推奨**:
- 中規模までは一括スイープ (e.g. 1 分ごと) を導入。`max_keys` 上限と LRU 退避でメモリを抑える。
- 製品化するなら Redis や Cloud Memorystore + token bucket。
- `X-Forwarded-For` の最左先頭 IP を信頼境界の上で採用 (Cloud Run の `X-Forwarded-For` はクライアント IP が含まれる)。

### 3.2 [中] 入力前処理の正規表現が脆い

**ファイル**: `app/services/calculator.py:109-170`

- `safe_eval` 冒頭で `long_dec_check` / `rep_check` / `mixed_check` を再宣言し、後段で同種の `long_dec_pattern` / `rep_pattern` / `pattern` を再度書いている (定義重複)。改修時に片方しか直さないバグを生む。
- `mixed_check` の正規表現 `(?P<sign>[-+]?)(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)` は、たとえば `1 1+2/3` のような式で意図せず `1 1+2/3` 部分にマッチしないものの、空白区切りの「帯分数入力」と「整数 + 別式」の境界が直感的でない。ユーザに対して「`2 2/3` は帯分数だが `2 2 + 3` はエラー」というルールを README に明記すると親切。
- 長い小数の正規表現は `\d{20,}` だが、`safe_eval` の長さチェック (100 文字) を回避するためのバイパス機構として機能している。長さ閾値とのインタラクションをドキュメント化したい (`MAX_EXPR_LENGTH_ABSOLUTE` までは通る、という仕様が暗黙)。

**推奨**:
- 正規表現をクラス属性 (`_LONG_DEC_RE`, `_REP_RE`, `_MIXED_RE`) としてコンパイル済みで集約。
- 各前処理を関数に分け、`safe_eval` は手順を順に呼ぶだけにする。
- バイパス対象パターンは `_BYPASS_PATTERNS = (...)` のような単一ソースから派生。

### 3.3 [小] エンドポイント層の二重実装

**ファイル**: `app/main.py:82-145`

- `/calculate` (HTML) と `/api/calculate` (JSON) が、ほぼ同じロジック (safe_eval → format_result → エラーハンドル) を別々に持つ。
- 差分は「テンプレートを返すか JSON を返すか」と「fraction_parts を返すか」のみ。

**推奨**: `_compute(expression, show_fraction)` のような共通関数を 1 つ作り、両エンドポイントは結果を整形して返すだけにする。

### 3.4 [小] HTML テンプレートに JS と CSS がインライン

**ファイル**: `app/templates/index.html`

- 195 行のうち 100+ 行が `<style>` / `<script>`。デザイントークン、ボタンフィット用の二分探索、HTMX afterSwap フックなどが混在。
- 静的アセットとして `app/static/calculator.css`, `app/static/calculator.js` に分離すれば、CSP (`unsafe-inline` 不要) や CDN キャッシュにも有利。
- インライン `style="..."` も多用。クラスベースに統一推奨。

### 3.5 [小] `os.getenv("ALLOW_POW")` を `Calculator.__init__` で読む

**ファイル**: `app/services/calculator.py:38-40`

- インスタンス生成時に env を読むため、テストでも `monkeypatch.setenv` 後に `Calculator()` を再生成する必要があり、`importlib.reload` が散見される。
- コンストラクタ引数 `allow_pow: bool | None = None` を受け取り、None のときだけ env を見るようにすると、依存注入とテスト容易性が両立する。

### 3.6 [小] ロギングが `logger.error(..., exc_info=True)` に対し `raise` で 500 をフレームワークに任せている

**ファイル**: `app/main.py:112-114`

- `/calculate` (HTML) では `Exception` を `raise` で再送し、TestClient/uvicorn 任せ。一方 `/api/calculate` は明示的に 500 JSON を返している。挙動が非対称。
- HTML 側でも 500 用エラーテンプレートを返したほうがユーザ体験が良い。

### 3.7 [小] テンプレート JS の `MutationObserver` 無限ループ余地

**ファイル**: `app/templates/index.html:184-188`

- `MutationObserver` が `.buttons` の `childList`/`subtree`/`characterData` を監視し、変更で `adjustAllButtons()` を呼ぶ。この関数自身が `btn.style.fontSize` を書き換えるため、`subtree:true` だと孫の `style` 属性変更でも発火する可能性。
- 現在は `style` は `attributes` ではなく要素プロパティ経由で書いているので影響は無いが、今後 `attribute` 監視を追加すると無限ループに陥りやすい。コメントで意図を残すか、`attributeFilter` を明示。

### 3.8 [小] Dockerfile

**ファイル**: `Dockerfile`

- `final` ステージは `base` をそのまま流用 (`COPY tests` も含むまま)。本番イメージにテストコードが入っているのは無駄であり (極小だが) 攻撃面でもある。
- `base` で `tests/` を `COPY` しているが、`final` で `RUN rm -rf tests` するか、ステージ分離で `final` には `app/` だけを `COPY --from=base` する設計が望ましい。
- `RUN pip install --no-cache-dir .` だが `uv.lock` をコピーしている割に `uv` を使っていない。`requirements` の決定論性を保つなら `uv pip sync uv.lock` または `pip install -r requirements.txt` (生成済み) に統一すべき。
- `compose.yaml` のヘルスチェックが `8000` 固定で、Cloud Run の 8080 と整合しない (compose は別環境なので機能上は OK だが、混乱の元)。

### 3.9 [小] `setup_cloud_run.sh`

- `gcloud config get-value project 2>/dev/null` の戻りに `(unset)` / `(none)` 両方をガード。良い。
- `--allow-unauthenticated` を無条件で付与。本番想定なら IAM 認証 + Cloud IAP のオプション化を検討。
- `MAX_INSTANCES` の最小値 (`--min-instances`) は未対応。コールドスタート抑制したい場合に追加検討。

### 3.10 [情報] テストの一貫性

- `tests/test_pow.py`, `tests/test_calculator_safety.py`, `tests/test_services_calculator.py::test_power_operator_behavior` が **べき乗の振る舞い** を重複してテストしている。
- べき乗関連は 1 ファイルに集約しても良い。

---

## 4. セキュリティ観点

| 項目 | 状態 | 備考 |
| --- | --- | --- |
| 任意コード実行 (eval) | ✅ | AST 評価で完全遮断、テスト済み |
| ReDoS | ⚠️ | 入力長 `MAX_EXPR_LENGTH_ABSOLUTE=20000` で実害は小だが、`re.sub` のバックトラックが理論上発生しうるパターンあり |
| DoS (深い再帰 / 巨大式) | ✅ | ノード数・深さ・指数・ベース上限 |
| 認証/認可 | ⚠️ | 公開 API。Cloud Run でも認証なし。レート制限のみ |
| CORS | ✅ | 許可オリジンを env 制御 |
| ヘッダ強化 | ❌ | `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy` 未設定 |
| CSRF | ⚠️ | フォーム POST だが state-changing ではない (副作用なし) ため低リスク。ただし `allow_credentials=True` と CORS の組み合わせは注意 |
| ロギング | ✅ | 例外を `exc_info` 付きで warn/error。PII は含まれず |

**推奨**: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy` (script-src 'self' など) を `add_middleware` で付与。

---

## 5. パフォーマンス観点

- `Fraction` の連鎖計算は分母が指数的に膨らむ場合がある (例: 連続的な巨大分母の和)。現在の `max_denominator=1000` は **表示用** のヒントで、計算用ではない。実際の計算上限は `_check_complexity` のみ。
- `fraction_to_repeating_decimal` は分母依存で最大 `max_decimal_digits=1000` ループ。十分速いが、`seen` dict のキー総数も上限になる。
- `static` ファイルは FastAPI から配信。Cloud Run 単独では問題なし。CDN (Cloud CDN) を入れる余地あり。

---

## 6. ドキュメント / メンテナンス観点

- `docs/` 以下に API・ARCHITECTURE・CI・USAGE などが整備されており、形式は良好。
- README にカバレッジ自動更新スクリプトがある (`scripts/update_readme_coverage.py`) のは良い実践。
- 一方、循環小数の波括弧記法 `0.{3}`、帯分数 `2 2/3` の入力仕様などは README/USAGE で利用者目線の例を増やすと親切。
- `.claude.bak/` がワーキングツリーに残っている。`.gitignore` 追加または削除を推奨。
- `.coverage`, `coverage.xml`, `node_modules/`, `calculator.egg-info/` がコミットツリー上に残存。`.gitignore` の見直し推奨。

---

## 7. 推奨優先順 (アクション)

1. **[High]** レート制限の `_rate_store` に上限とスイープを導入し、Cloud Run 環境では分散ストアか `X-Forwarded-For` 採用に切り替える。
2. **[Med]** `Calculator.safe_eval` の正規表現重複を排除し、前処理を関数に切り出す。
3. **[Med]** `/calculate` と `/api/calculate` で共通ロジックを抽出する。
4. **[Med]** セキュリティヘッダのミドルウェアを追加する。
5. **[Low]** `index.html` の CSS / JS を静的アセットへ分離し CSP に備える。
6. **[Low]** Dockerfile の `final` ステージから `tests/` を排除。
7. **[Low]** `Calculator.__init__` で `ALLOW_POW` を引数化し、テストの `importlib.reload` を削減する。
8. **[Low]** べき乗関連テストの重複を整理する。
9. **[Low]** `.coverage`, `coverage.xml`, `node_modules/`, `.claude.bak/` を `.gitignore` 経由で除外。

---

## 8. まとめ

- **強み**: 安全性 (AST 評価)、正確算術 (Fraction)、循環小数の往復一致、層別テスト、Cloud Run まで含めた CI/CD パイプライン。
- **弱み**: シングルプロセス前提のレート制限、入力前処理の正規表現重複、ビュー層の責務集中、セキュリティヘッダ未設定。
- 学習プロジェクトとしては完成度が高く、上記 1〜4 を対応すれば「軽量だが本番に出せる電卓 SaaS」として十分耐えるレベルです。
