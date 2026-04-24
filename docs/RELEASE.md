リリース手順

1. 全テストとCIが成功していることを確認
2. バージョンを pyproject.toml の version に反映
3. タグ作成: git tag -a vX.Y.Z -m "release vX.Y.Z"
4. リモートへ push: git push origin main --tags

（必要ならDockerイメージをビルドし、レジストリへ push）
