# gahaku 開発メモ

公開リポジトリ（MIT）。Claude Code のプラグインで、中身はスキル1つとスクリプト1本だけ。

| 場所 | 中身 |
|---|---|
| `skills/gahaku/SKILL.md` | 手順：プロンプトを書く → 生成 → 文字の照合 |
| `skills/gahaku/generate.py` | OpenAI の画像 API を1回呼んで保存する。標準ライブラリのみ |
| `.claude-plugin/` | `plugin.json` と `marketplace.json`（このリポジトリ自体がマーケットプレイス） |

## 決まりごと

- **小さく保つ。** サイト固有の画風・投稿処理・費用の記録は、呼び出す側のプロジェクトに置く
- **`generate.py` は依存を足さない**（`python3` だけで動くこと）
- `.env`・API キー・生成した画像をコミットしない

## リリース

1. `.claude-plugin/plugin.json` の `version` を上げる
2. 料金が変わっていれば `generate.py` の `RATE` と確認日を直す
3. 下の確認をしてから、タグ `vX.Y.Z` を打つ

## 確認

API を呼ぶので費用がかかる。`--quality low --n 1` で試す。

```bash
python3 skills/gahaku/generate.py --out output/test.png --size 1200x800 --quality low --prompt "..."
```
