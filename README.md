# gahaku（画伯）

OpenAI の画像 API で、**ブログのアイキャッチ**（タイトル入り）と**サイトの画像素材**を作る CLI と、Claude Code のプラグインです。

- **CLI（`gahaku`）**: デザイン設定（JSON）と場面の説明を受け取り、画像を返す。WordPress や Astro のことは知らないので、どのサイトからでも使える
- **Claude Code プラグイン**: 生成 → Claude Code がタイトルを1文字ずつ照合 → 誤字があればやり直す、までを手順にしたスキル

> English summary: A CLI and Claude Code plugin that generates blog eyecatch images (with Japanese titles) and website image assets via the OpenAI Images API. Site-specific design lives in a JSON file you pass in.

## 必要なもの

- [uv](https://docs.astral.sh/uv/)（Python 3.10 以上）
- OpenAI の API キー（**利用料は使う人の負担**です）

## インストール

### CLI

```bash
uv tool install git+https://github.com/hdmt/gahaku
```

バージョンを固定して使うなら、タグを指定します。

```bash
uvx --from git+https://github.com/hdmt/gahaku@v0.1.0 gahaku --help
```

### Claude Code プラグイン

Claude Code の中で、このリポジトリをマーケットプレイスとして追加し、プラグインを入れます。

```
/plugin marketplace add hdmt/gahaku
/plugin install gahaku@gahaku
```

入るスキルは2つです。

| スキル | 使いどころ |
|---|---|
| `gahaku:eyecatch` | 記事のアイキャッチ。写真 → タイトル入れ → 文字の照合 |
| `gahaku:asset` | サイトの画像素材。ヒーロー画像・背景・挿絵・透過イラストなど、文字の入らない画像 |

### API キー

環境変数 `OPENAI_API_KEY`、無ければ `~/.config/gahaku/.env` から読みます。

```bash
mkdir -p ~/.config/gahaku
echo 'OPENAI_API_KEY=sk-...' > ~/.config/gahaku/.env
chmod 600 ~/.config/gahaku/.env
```

## 使い方

```bash
# 送るプロンプトの確認（API は呼ばない）
gahaku prompt --design design.json --scene "A person reviewing documents at a bright desk." \
  --title-space --title "費用相場｜月額・初期費用の内訳"

# 1. 写真を作る（文字なし）。--n 2 なら photo-1.png, photo-2.png
gahaku photo --design design.json --scene "..." --title-space --out out/photo.png --n 2

# 2. 写真にタイトルを載せる
gahaku title --design design.json --photo out/photo-1.png \
  --title "費用相場｜月額・初期費用の内訳" --out out/eyecatch.png --n 2

# サイトの素材（透過のイラスト）
gahaku photo --design flat.json --scene "..." --size 1024x1024 \
  --background transparent --out public/images/spot.webp

# 費用の記録と集計
gahaku photo ... --cost-log out/gahaku-cost.csv
gahaku cost --cost-log out/gahaku-cost.csv
```

### よく使うオプション

| オプション | 中身 |
|---|---|
| `--design` | デザイン設定のパス（必須） |
| `--size` | 仕上がりサイズ。`1200x800` か、デザイン設定の `sizes` の名前。`title` では省略すると写真と同じ |
| `--n` | 候補の枚数（1〜10） |
| `--ref` | 参考画像。`photo` ではトーンを揃える（複数可）、`title` では文字デザインを揃える |
| `--main` `--sub` `--label` | 画像に入れる文言を上書きする。空文字でその行を消す |
| `--model` `--quality` | デザイン設定の値を上書きする |
| `--background` | `transparent` / `opaque` / `auto` |
| `--cost-log` | 費用を記録する CSV。同じモデル・サイズ・品質の記録があれば、次から見積もりも出る |
| `--json` | 結果を JSON で出す（呼び出す側が記録に使う） |

`--json` の出力:

```json
{"stage": "title", "files": ["out/eyecatch-1.png", "out/eyecatch-2.png"], "usd": 0.31, "usd_per_image": 0.155,
 "model": "gpt-image-2.5-sunburst", "quality": "high", "size": "1200x800", "request_size": "1200x800",
 "usage": {"text_in": 420, "image_in": 1500, "image_out": 9800},
 "text": {"label": "", "main": "費用相場", "sub": "月額・初期費用の内訳"}}
```

保存の形式は `--out` の拡張子で決まります（`.png` / `.webp` / `.jpg`）。

## デザイン設定（`design.json`）

サイトごとの画風・文字デザインを1ファイルにまとめます。例は [`examples/designs/`](examples/designs/) にあります。

```json
{
  "model": "gpt-image-2.5-sunburst",
  "quality": "high",
  "size": "eyecatch",
  "sizes": { "eyecatch": "1200x800", "og": "1200x630" },
  "style": "...",
  "people": "...",
  "constraints": "...",
  "title": { "label": "", "design": "..." }
}
```

| 項目 | 必須 | 中身 |
|---|---|---|
| `style` | ○ | 画風（英語）。写真かイラストか、光、色、雰囲気 |
| `constraints` | ○ | 禁止事項（英語）。文字・ロゴを入れない、コラージュにしない、など |
| `people` | | 人物を描くときの決まり（英語） |
| `model` | | 使うモデル。省略時は `gpt-image-2.5-sunburst` |
| `quality` | | `low` / `medium` / `high` / `xhigh` / `max` / `auto`。省略時は `high` |
| `size` | | 既定の仕上がりサイズ。`1200x800` か `sizes` の名前 |
| `sizes` | | 用途ごとのサイズに名前を付ける |
| `title.design` | アイキャッチなら○ | タイトルの文字デザイン（英語）。書体、色、帯、位置 |
| `title.label` | | メインの上に小さく出すラベル（例: カテゴリ名）。空なら出さない |

### サイズについて

gpt-image-2 以降のモデルは、幅・高さが16の倍数で、縦横比が1:3〜3:1なら好きなサイズを指定できます（最大 3840x2160）。
`1200x800` や `1024x1024` のように条件を満たすサイズは、そのまま頼みます。条件に合わないサイズ（`1200x630`、`1920x1080` など）は、近いサイズ（`1200x624`、`1920x1088`）で作ってから切り抜き・縮小します。

## 料金

トークン課金です。1枚あたりの費用はサイズ・品質・参考画像の有無で変わります。
`src/gahaku/pricing.py` の `PRICES` に料金表があり、確認日と出典（[OpenAI の料金ページ](https://developers.openai.com/api/docs/pricing)）を書いています。料金が変わっていたら、ここを直してください。

アイキャッチは、写真とタイトル入れで**最低2回**の生成になります。`--n 2` なら4枚分です。

## 注意

- **OpenAI の画像 API の利用料は、使う人の負担です**
- 画像の文字はモデルが描くため、誤字が出ることがあります。プラグインは Claude Code に照合させますが、それでも見落としはありえます。**公開前に、必ず人が文字を確認してください**
- 実在の人物・企業ロゴ・ブランドを描かせないでください
- 生成した画像の利用条件は、OpenAI の利用規約に従います

## 開発

```bash
uv sync
uv run pytest
uv run gahaku --help
```

## ライセンス

MIT
