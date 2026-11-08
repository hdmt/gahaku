# gahaku

English | [日本語](README_ja.md)

A Claude Code plugin that generates images with the OpenAI Images API — blog eyecatches with rendered titles (including Japanese), and website assets such as hero images, backgrounds and illustrations.

*Gahaku* (画伯) is Japanese for "master painter".

Ask Claude Code something like:

```
Make an eyecatch image for the article "How to Start Working from Home | Tools and Setup", with the title on it.
```

and it will:

1. Work out the scene and the title layout from the article title, and write the prompt
2. Call the OpenAI Images API through `generate.py` and save the image
3. Read the text in the image character by character, compare it with the requested title, and regenerate if there is a typo

## Install

In Claude Code:

```
/plugin marketplace add hdmt/gahaku
/plugin install gahaku@gahaku
```

The only requirement is Python 3.10+ (`generate.py` uses the standard library only).

### API key

The key is read from the `OPENAI_API_KEY` environment variable, or from `~/.config/gahaku/.env`.

```bash
mkdir -p ~/.config/gahaku && touch ~/.config/gahaku/.env && chmod 600 ~/.config/gahaku/.env
# then add a line: OPENAI_API_KEY=sk-...
```

A restricted key that only allows Images (`/v1/images`) is enough.

## Using generate.py directly

```bash
python3 skills/gahaku/generate.py --out eyecatch.png --size 1200x800 --n 2 <<'EOF'
A blog eyecatch image ...
EOF
```

| Option | Description |
|---|---|
| `--out` | Output path (.png / .webp / .jpg). With `--n 2` or more, `-1`, `-2`, … are appended |
| `--prompt` | The prompt. Read from stdin if omitted |
| `--size` | `WIDTHxHEIGHT`. Both sides must be multiples of 16, aspect ratio between 1:3 and 3:1. Default `1536x1024` |
| `--n` | Number of images (1–10) |
| `--ref` | Reference image(s) to match design or tone. Can be repeated |
| `--quality` | `low` / `medium` / `high` (default) / `xhigh` / `max` / `auto` |
| `--model` | Default `gpt-image-2.5-sunburst` |
| `--background` | `transparent` / `opaque` / `auto` |

The result is printed as JSON:

```json
{"files": ["eyecatch-1.png", "eyecatch-2.png"], "model": "gpt-image-2.5-sunburst", "size": "1200x800",
 "quality": "high", "usage": {"text_in": 330, "image_in": 0, "image_out": 4200}, "usd": 0.12765}
```

`usd` is an estimate: token usage multiplied by the rates in `RATE` in `generate.py`.

## Notes

- **You pay for your own OpenAI API usage.**
- Text in the image is drawn by the model and can contain typos. Claude Code proofreads it, but may still miss something. **Always have a person check the text before publishing.**
- Do not ask for real people, company logos or brands.

## License

MIT
