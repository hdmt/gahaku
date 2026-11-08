# gahaku 開発メモ

公開リポジトリ（MIT）。OpenAI の画像 API で、ブログのアイキャッチとサイトの画像素材を作る CLI と、Claude Code プラグイン。

## 構成

| 場所 | 中身 |
|---|---|
| `src/gahaku/cli.py` | CLI（`prompt` / `photo` / `title` / `cost`） |
| `src/gahaku/prompts.py` | 写真・タイトル入れのプロンプト組み立て |
| `src/gahaku/pricing.py` | 料金表 `PRICES`（確認日・出典つき）と費用の記録 |
| `src/gahaku/api.py` | images/generations・images/edits の呼び出し（標準ライブラリのみ） |
| `src/gahaku/config.py` | デザイン設定・API キー・サイズの計算 |
| `skills/eyecatch/`・`skills/asset/` | プラグインのスキル |
| `.claude-plugin/` | `plugin.json` と `marketplace.json`（このリポジトリ自体がマーケットプレイス） |
| `examples/designs/` | 汎用のデザイン例 |

## 決まりごと

- **サイト固有のものを入れない。** 実在サイトの名前・配色・プロンプト・投稿処理は、呼び出す側のリポジトリに置く
- **取り決めは CLI の引数と `--json` の出力だけ。** 変えるときはバージョンを上げ、README を直す。呼び出し側はタグで固定している
- **`.env`・API キー・生成した画像・費用の CSV をコミットしない**（`.gitignore` 済み。`examples/` の画像は除く）
- 依存は Pillow だけにする

## リリース

1. `pyproject.toml`・`src/gahaku/__init__.py`・`.claude-plugin/plugin.json` のバージョンを揃えて上げる
2. 料金が変わっていれば `pricing.py` の `PRICES` と `PRICES_CHECKED` を直す
3. `uv run pytest` を通す
4. タグ `vX.Y.Z` を打つ

## 確認

```bash
uv run pytest
uv run gahaku prompt --design examples/designs/corporate.json --scene "..." --title "メイン｜サブ"
```

API を呼ぶ `photo` / `title` は費用がかかる。動作確認で呼ぶときは `--quality low --n 1` にする。
