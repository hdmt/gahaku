# gahaku（画伯）

[English](README.md) | 日本語

Claude Code から OpenAI の画像 API で画像を作るプラグインです。ブログのアイキャッチ（タイトルの文字入り）や、サイトの画像素材に使えます。

```
アイキャッチ画像作って。記事タイトル「〇〇」に沿った内容で、テキストも入れて
```

と頼むと、Claude Code が次のように進めます。

1. タイトルから絵の内容と文字の入れ方を考え、プロンプトを書く
2. `generate.py` が OpenAI の画像 API を呼び、画像を保存する
3. 画像の文字を1文字ずつ照合し、誤字があれば作り直す

## インストール

Claude Code の中で実行します。

```
/plugin marketplace add hdmt/gahaku
/plugin install gahaku@gahaku
```

必要なのは Python 3.10 以上だけです（`generate.py` は標準ライブラリで動きます）。

### API キー

環境変数 `OPENAI_API_KEY`、無ければ `~/.config/gahaku/.env` から読みます。

```bash
mkdir -p ~/.config/gahaku && touch ~/.config/gahaku/.env && chmod 600 ~/.config/gahaku/.env
# ~/.config/gahaku/.env に OPENAI_API_KEY=sk-... と書く
```

キーの権限は Restricted で、Images（`/v1/images`）だけ許可すれば足ります。

## generate.py だけ使う

```bash
python3 skills/gahaku/generate.py --out eyecatch.png --size 1200x800 --n 2 <<'EOF'
A blog eyecatch image ...
EOF
```

| オプション | 中身 |
|---|---|
| `--out` | 保存先（.png / .webp / .jpg）。`--n 2` 以上なら `-1`, `-2` を付ける |
| `--prompt` | プロンプト。省略時は標準入力から読む |
| `--size` | `WIDTHxHEIGHT`。幅・高さは16の倍数、縦横比1:3〜3:1。既定 `1536x1024` |
| `--n` | 枚数（1〜10） |
| `--ref` | 参考画像（複数可）。デザインやトーンを揃える |
| `--quality` | `low` / `medium` / `high`（既定）/ `xhigh` / `max` / `auto` |
| `--model` | 既定 `gpt-image-2.5-sunburst` |
| `--background` | `transparent` / `opaque` / `auto` |

結果は JSON で出ます。

```json
{"files": ["eyecatch-1.png", "eyecatch-2.png"], "model": "gpt-image-2.5-sunburst", "size": "1200x800",
 "quality": "high", "usage": {"text_in": 330, "image_in": 0, "image_out": 4200}, "usd": 0.12765}
```

`usd` は、使用トークンに料金（`generate.py` の `RATE`）を掛けた概算です。

## 注意

- **OpenAI の API の利用料は、使う人の負担です**
- 画像の文字はモデルが描くため、誤字が出ることがあります。Claude Code が照合しますが、見落としはありえます。**公開前に、必ず人が文字を確認してください**
- 実在の人物・企業ロゴ・ブランドを描かせないでください

## ライセンス

MIT
