ブランチ保護ルール（推奨設定）

対象ブランチ: main, master

推奨設定:
- プルリクエスト必須: 直接の push を禁止
- レビュー: マージ前に少なくとも1件の承認レビューを必須にする
- コードオーナー: CODEOWNERS を使って特定ディレクトリのレビューを必須化
- ステータスチェック: 以下のチェックが成功することを必須にする
  - test-and-lint (ユニットテスト + lint + mypy)
  - docker-build-check (イメージビルド検証)
  - e2e (必要に応じて main で必須化)
- 最新コミット適用: マージ前にブランチを最新に更新（Require branches to be up to date）
- 承認の失効: 新しいコミットで既存の承認を取り消す
- 管理者にも適用: "Enforce for administrators" を有効にする

運用メモ:
- CODEOWNERS を設定するとレビュールールが自動化される
- Playwright E2E は実行コストが高いため、通常は別ワークフローで main のみ必須にする

適用方法（手動）:
1. GitHub リポジトリの Settings → Branches → Add rule
2. Branch name pattern に `main` を指定
3. 上記オプションをチェックして Save

自動化（gh CLI 例）:
# 例: 必要に応じてアクセストークンを env に設定して実行
# gh api --method PUT repos/:owner/:repo/branches/main/protection -f required_status_checks.contexts='["test-and-lint"]' -f required_pull_request_reviews.dismiss_stale_reviews=true

必要ならこのルールを実際に API/gh で適用します。実行しますか？