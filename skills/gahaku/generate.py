#!/usr/bin/env python3
"""OpenAI の画像 API を1回呼び、画像を保存する。標準ライブラリだけで動く。

    python3 generate.py --out eyecatch.png [--size 1200x800] [--n 2] [--ref 参考.png] <<'EOF'
    （プロンプト）
    EOF

プロンプトは標準入力か --prompt で渡す。--ref があれば images/edits（参考画像つき）、無ければ images/generations。
API キーは環境変数 OPENAI_API_KEY、無ければ ~/.config/gahaku/.env から読む。
結果は JSON で標準出力に出す（保存したファイル、使用トークン、概算の費用）。
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = "https://api.openai.com/v1/images"
ENV_FILE = Path.home() / ".config" / "gahaku" / ".env"
# USD / 100万トークン。gpt-image-2 以降の料金（2026-11-08 確認、https://developers.openai.com/api/docs/pricing）
RATE = {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00}
FORMATS = {".png": "png", ".webp": "webp", ".jpg": "jpeg", ".jpeg": "jpeg"}


def fail(msg):
    sys.exit(f"generate.py: {msg}")


def api_key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() == "OPENAI_API_KEY" and v.strip():
                return v.strip().strip("\"'")
    fail(f"OPENAI_API_KEY が無い。環境変数か {ENV_FILE} に設定する")


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for p in files:
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        out.append(f'--{b}\r\nContent-Disposition: form-data; name="image[]"; filename="{p.name}"\r\n'
                   f"Content-Type: {mime}\r\n\r\n".encode() + p.read_bytes() + b"\r\n")
    out.append(f"--{b}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={b}"


def call(params, refs):
    if refs:
        body, ctype = multipart(params, refs)
        url = f"{API}/edits"
    else:
        body, ctype = json.dumps(params).encode(), "application/json"
        url = f"{API}/generations"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", ctype)
    req.add_header("Authorization", f"Bearer {api_key()}")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        fail(f"OpenAI API {e.code}: {e.read().decode(errors='replace')[:800]}")
    except urllib.error.URLError as e:
        fail(f"OpenAI API に接続できない: {e.reason}")


def main():
    ap = argparse.ArgumentParser(description="OpenAI の画像 API で画像を1回生成して保存する")
    ap.add_argument("--out", required=True, help="保存先（.png/.webp/.jpg）。--n 2 以上なら -1, -2 … を付ける")
    ap.add_argument("--prompt", help="プロンプト。省略時は標準入力から読む")
    ap.add_argument("--size", default="1536x1024", help="WIDTHxHEIGHT。幅・高さは16の倍数、縦横比1:3〜3:1（既定 1536x1024）")
    ap.add_argument("--n", type=int, default=1, help="枚数（1〜10）")
    ap.add_argument("--ref", action="append", default=[], help="参考画像（複数可）。デザインやトーンを揃える")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high", "xhigh", "max", "auto"])
    ap.add_argument("--model", default="gpt-image-2.5-sunburst")
    ap.add_argument("--background", choices=["transparent", "opaque", "auto"])
    a = ap.parse_args()

    prompt = a.prompt if a.prompt is not None else sys.stdin.read()
    if not prompt.strip():
        fail("プロンプトが空")
    out = Path(a.out)
    fmt = FORMATS.get(out.suffix.lower()) or fail(f"拡張子は {' / '.join(FORMATS)} のどれか: {out}")
    try:
        w, h = (int(v) for v in a.size.lower().split("x"))
    except ValueError:
        fail(f"--size は WIDTHxHEIGHT: {a.size}")
    if w % 16 or h % 16:
        fail(f"--size の幅・高さは16の倍数にする: {a.size}（例: 1200x800, 1536x1024, 1920x1088）")
    if not 1 <= a.n <= 10:
        fail("--n は 1〜10")
    if a.background == "transparent" and fmt == "jpeg":
        fail("透過背景は .png か .webp で保存する")
    refs = [Path(r) for r in a.ref]
    for r in refs:
        if not r.exists():
            fail(f"参考画像が無い: {r}")

    params = {"model": a.model, "prompt": prompt, "n": a.n, "size": f"{w}x{h}",
              "quality": a.quality, "output_format": fmt}
    if a.background:
        params["background"] = a.background
    res = call(params, refs)
    if not res.get("data"):
        fail(f"画像が返ってこなかった: {json.dumps(res, ensure_ascii=False)[:800]}")

    out.parent.mkdir(parents=True, exist_ok=True)
    paths = [out] if len(res["data"]) == 1 else \
        [out.with_name(f"{out.stem}-{i}{out.suffix}") for i in range(1, len(res["data"]) + 1)]
    for d, p in zip(res["data"], paths):
        p.write_bytes(base64.b64decode(d["b64_json"]))

    u = res.get("usage") or {}
    det = u.get("input_tokens_details") or {}
    usage = {"text_in": det.get("text_tokens", 0), "image_in": det.get("image_tokens", 0),
             "image_out": u.get("output_tokens", 0)}
    usd = sum(usage[k] * RATE[k] for k in RATE) / 1e6
    print(json.dumps({"files": [str(p) for p in paths], "model": a.model, "size": f"{w}x{h}",
                      "quality": a.quality, "usage": usage, "usd": round(usd, 5)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
