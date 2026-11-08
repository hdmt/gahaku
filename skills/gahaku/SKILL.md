---
name: gahaku
description: OpenAI の画像 API で画像を作る。ブログのアイキャッチ（記事タイトルの文字入り）、サイトのヒーロー画像・背景・挿絵・透過イラストなどに使う。「アイキャッチ作って」「サムネ画像」「記事の画像」「サイトの画像」「挿絵」、英語なら featured image・thumbnail・hero image のように、画像が要るときに使う。文字を入れた画像は、Claude Code が1文字ずつ照合してから渡す。
---

# 画像の作成

プロンプトは Claude Code が書き、画像は同じフォルダの `generate.py` が OpenAI の画像 API で作る。文字入りの画像は、渡す前に Claude Code が文字を照合する。

## 準備

API キーは環境変数 `OPENAI_API_KEY` か `~/.config/gahaku/.env`（`OPENAI_API_KEY=sk-...`）に要る。
無いと言われたら、ユーザー自身に設定してもらう。**キーをチャットに貼ってもらわない。**

## 1. 決める

依頼から読み取り、足りないものだけ聞く。

| 項目 | 既定 |
|---|---|
| 入れる文字 | アイキャッチなら記事タイトル。長ければ「メイン」と「サブ」に分ける（`｜` があればそこで分ける）。素材画像なら文字なし |
| 絵の内容 | タイトルや記事の内容から考える |
| 画風・文字デザイン | プロジェクトの CLAUDE.md などに決まりがあれば従う。既存のアイキャッチがあれば `--ref` に渡して揃える |
| サイズ | アイキャッチ `1200x800`、OGP `1200x624`、ヒーロー `1920x1088`、正方形 `1024x1024`（幅・高さは16の倍数） |
| 出力先 | プロジェクトの決まりに従う。無ければ聞く。拡張子で形式が決まる（.png / .webp / .jpg） |

## 2. プロンプトを書く

英語で書き、入れる文字だけは日本語のまま `"..."` で囲み、文字数を添える。

```
A featured (header) image for a blog post titled "{記事タイトル}".

Scene: {何が写っているか。被写体は1〜2つ}
Style: {写真かイラストか、光、色、雰囲気}

Text to render. Copy each string exactly, character by character; do not translate, add, omit or reorder characters. The double quotes are delimiters only.
- Main title (largest): "{メイン}" ({文字数} characters)
- Subtitle: "{サブ}" ({文字数} characters)

Title design: {書体、色、帯や背景、位置。人物の顔にかけない。余白を十分に取る}

Constraints: Render only the text listed above. Japanese characters must be correct and complete. No other text, logos, watermarks or signage. No identifiable real people, brands or company uniforms.
```

文字なしの素材画像では、Text と Title design の段落を外し、Constraints を `No text, letters, numbers, logos or watermarks anywhere.` にする。

## 3. 生成する

```bash
python3 {このスキルのディレクトリ}/generate.py --out {出力先} --size 1200x800 --n 2 <<'EOF'
{プロンプト}
EOF
```

- `--ref 画像` で参考画像を渡せる（複数可）。デザインやトーンを揃えるときに使う
- `--background transparent` で透過背景（.png か .webp）
- 費用は1枚数円〜数十円。結果の JSON の `usd` に概算が出る。試すだけなら `--quality low`

## 4. 確認する

生成された画像を**1枚ずつ自分で開いて見る**。

文字入りの画像は、次の順で照合する。

1. **書き起こす**: 画像の文字を、見えたとおり1文字ずつ書き起こす。正解を見ながら読まない（思い込みで読み飛ばすため）
2. **照合する**: 書き起こしとプロンプトの文字列を1文字ずつ比べる。改行の位置は問わない。似た別の字（運↔連、機↔幾、援↔授など）、画の欠け、送り仮名・助詞の抜け、記号の違いに注意する
3. **余計な文字**: 指定外の文字・ロゴ・透かし・崩れた文字列が無いか

あわせて、顔・手・物の形が不自然でないか、文字がはみ出したり顔にかかったりしていないかも見る。

- **問題が無い候補がある**: 照合の結果を添えて、その候補を勧める
- **誤字がある**: 誤字のあった候補を `--ref` に渡して、「文字だけ直す」プロンプトで作り直す。**やり直しは2回まで**。それでも直らなければ、文言を短くする案と、ここまでの費用を添えてユーザーに返す

照合は目視なので見落としがありうる。**公開前に人が文字を確認する**よう必ず伝える。

## 5. 渡す

採用した画像のパスと、かかった費用（`usd` の合計）を伝える。使わなかった候補を消すかどうかはユーザーに聞く。
投稿やアップロードはしない（頼まれたら、呼び出した側のプロジェクトの方法で行う）。
