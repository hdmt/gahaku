"""gahaku: OpenAI の画像 API で、ブログのアイキャッチやサイトの画像素材を作る。

    gahaku prompt --design d.json --scene "..." [--title "メイン｜サブ"]   # 送る内容の確認（API は呼ばない）
    gahaku photo  --design d.json --scene "..." --out a.png [--n 2] [--size eyecatch] [--ref r.png]
    gahaku title  --design d.json --photo a.png --title "メイン｜サブ" --out b.png [--n 2]
    gahaku cost   --cost-log cost.csv

画像の文字が正しいかどうかは、このツールでは判定しない（呼び出す側が目で確かめる）。
"""

import argparse
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

from . import __version__, api, pricing
from .config import GahakuError, api_key, default_size, load_design, parse_size, request_size
from .prompts import photo_prompt, title_prompt, title_text

FORMATS = {".png": "png", ".webp": "webp", ".jpg": "jpeg", ".jpeg": "jpeg"}


def log(msg):
    print(msg, file=sys.stderr)


def output_paths(out, n):
    p = Path(out)
    if n == 1:
        return [p]
    return [p.with_name(f"{p.stem}-{i}{p.suffix}") for i in range(1, n + 1)]


def output_format(out):
    fmt = FORMATS.get(Path(out).suffix.lower())
    if not fmt:
        raise GahakuError(f"保存先の拡張子は {' / '.join(FORMATS)} のどれか: {out}")
    return fmt


def fit(img, size):
    """縦横比が違えば中央で切り抜き、仕上がりサイズに縮小する。"""
    w, h = size
    if img.size == (w, h):
        return img
    iw, ih = img.size
    target = w / h
    if iw / ih > target:
        cw = round(ih * target)
        img = img.crop(((iw - cw) // 2, 0, (iw - cw) // 2 + cw, ih))
    elif iw / ih < target:
        ch = round(iw / target)
        img = img.crop((0, (ih - ch) // 2, iw, (ih - ch) // 2 + ch))
    return img.resize((w, h), Image.LANCZOS)


def save(data, path, size, fmt):
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") and fmt != "jpeg" else "RGB")
    img = fit(img, size)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jpeg":
        img.save(path, "JPEG", quality=90, optimize=True)
    elif fmt == "webp":
        img.save(path, "WEBP", quality=90)
    else:
        img.save(path, "PNG", optimize=True)


def run(a, cfg, stage, prompt, images, size, extra=None):
    n = a.n
    if not 1 <= n <= 10:
        raise GahakuError("--n は 1〜10")
    fmt = output_format(a.out)
    if a.background == "transparent" and fmt == "jpeg":
        raise GahakuError("透過背景は .png か .webp で保存する")
    model = a.model or cfg["model"]
    quality = a.quality or cfg["quality"]
    rw, rh = request_size(*size)
    size_s = f"{size[0]}x{size[1]}"

    params = {"model": model, "prompt": prompt, "n": n, "size": f"{rw}x{rh}",
              "quality": quality, "output_format": "webp" if fmt == "webp" else "png"}
    if a.background:
        params["background"] = a.background

    est = pricing.estimate(a.cost_log, stage, model, size_s, quality) if a.cost_log else None
    log(f"生成: {stage} / {model} / {quality} / {size_s}（API には {rw}x{rh}）× {n}枚")
    if est:
        log(f"見積もり: 1枚あたり {pricing.fmt(est[0])}（過去{est[1]}枚の平均）")

    key = api_key()
    res = api.edit(key, params, images) if images else api.generate(key, params)

    paths = output_paths(a.out, len(res["data"]))
    for d, p in zip(res["data"], paths):
        save(base64.b64decode(d["b64_json"]), p, size, fmt)

    c = pricing.cost(model, res.get("usage") or {})
    per = c["usd"] / len(paths) if c["usd"] is not None else None
    if a.cost_log:
        pricing.log_rows(a.cost_log, [{
            "at": pricing.now(), "stage": stage, "model": model, "size": size_s, "quality": quality,
            "out": str(p), "text_in": c["text_in"], "image_in": c["image_in"], "image_out": c["image_out"],
            "usd": f"{per:.5f}" if per is not None else "",
        } for p in paths])

    result = {"stage": stage, "files": [str(p) for p in paths], "usd": c["usd"], "usd_per_image": per,
              "model": model, "quality": quality, "size": size_s, "request_size": f"{rw}x{rh}",
              "usage": {k: c[k] for k in ("text_in", "image_in", "image_out")}}
    result.update(extra or {})

    if a.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for p in paths:
            print(p)
        print(f"合計: {pricing.fmt(c['usd'])}  (テキスト入力{c['text_in']} / 画像入力{c['image_in']} / 出力{c['image_out']} トークン)")
        if "text" in result:
            print("照合する文字列: " + json.dumps(result["text"], ensure_ascii=False))


def cmd_prompt(a):
    cfg = load_design(a.design)
    size = parse_size(a.size, cfg) if a.size else default_size(cfg)
    model = a.model or cfg["model"]
    quality = a.quality or cfg["quality"]
    if not a.scene and not a.title:
        raise GahakuError("--scene か --title のどちらかが要る")
    if a.scene:
        print("===== photo =====")
        print(photo_prompt(cfg, a.scene, size, title_space=a.title_space, n_refs=a.refs))
    if a.title:
        text = title_text(cfg, a.title, a.main, a.sub, a.label)
        print("\n===== title =====")
        print(title_prompt(cfg, text, has_ref=a.refs > 0))
        print("\n照合する文字列: " + json.dumps(text, ensure_ascii=False))
    rw, rh = request_size(*size)
    print(f"\n# {model} / {quality} / {size[0]}x{size[1]}（API には {rw}x{rh}）")
    size_s = f"{size[0]}x{size[1]}"
    for stage in [s for s, on in (("photo", a.scene), ("title", a.title)) if on]:
        est = pricing.estimate(a.cost_log, stage, model, size_s, quality) if a.cost_log else None
        if est:
            print(f"# 見積もり（{stage}）: 1枚あたり {pricing.fmt(est[0])}（過去{est[1]}枚の平均）")
        else:
            p = pricing.price(model)
            rate = f"画像出力 ${p['image_out']}/100万トークン" if p else "料金表に無いモデル"
            print(f"# 見積もり（{stage}）: 記録が無いため不明（{rate}、料金 {pricing.PRICES_CHECKED} 時点）")


def cmd_photo(a):
    cfg = load_design(a.design)
    size = parse_size(a.size, cfg) if a.size else default_size(cfg)
    prompt = photo_prompt(cfg, a.scene, size, title_space=a.title_space, n_refs=len(a.ref))
    run(a, cfg, "photo", prompt, a.ref, size)


def cmd_title(a):
    cfg = load_design(a.design)
    if not Path(a.photo).exists():
        raise GahakuError(f"写真が無い: {a.photo}")
    if a.size:
        size = parse_size(a.size, cfg)
    else:
        with Image.open(a.photo) as im:
            size = im.size
    text = title_text(cfg, a.title or "", a.main, a.sub, a.label)
    if not text["main"]:
        raise GahakuError("メインのタイトルが空")
    try:
        prompt = title_prompt(cfg, text, has_ref=bool(a.ref))
    except ValueError as e:
        raise GahakuError(f"{a.design}: {e}") from e
    images = [a.photo] + ([a.ref] if a.ref else [])
    run(a, cfg, "title", prompt, images, size, {"text": text})


def cmd_cost(a):
    months = pricing.monthly(a.cost_log)
    if not months:
        raise GahakuError(f"記録が無い: {a.cost_log}")
    for m, (cnt, usd) in months.items():
        print(f"{m}  {cnt}枚  {pricing.fmt(usd)}")


def build_parser():
    ap = argparse.ArgumentParser(prog="gahaku", description="OpenAI の画像 API で画像を作る")
    ap.add_argument("--version", action="version", version=f"gahaku {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, *, generate=True):
        sp.add_argument("--design", required=True, help="デザイン設定（JSON）のパス")
        sp.add_argument("--size", help="仕上がりサイズ。1200x800 か、デザイン設定の sizes の名前")
        sp.add_argument("--model", help="デザイン設定の model を上書きする")
        sp.add_argument("--quality", choices=["low", "medium", "high", "xhigh", "max", "auto"],
                        help="デザイン設定の quality を上書きする")
        sp.add_argument("--cost-log", help="費用を記録する CSV。見積もりにも使う（省略時は記録しない）")
        if generate:
            sp.add_argument("--out", required=True, help="保存先（.png/.webp/.jpg）。n>1 なら -1, -2 … を付ける")
            sp.add_argument("--n", type=int, default=1, help="候補の枚数（1〜10）")
            sp.add_argument("--background", choices=["transparent", "opaque", "auto"], help="背景")
            sp.add_argument("--json", action="store_true", help="結果を JSON で標準出力に出す")

    def title_args(sp):
        sp.add_argument("--title", help="タイトル。｜の前がメイン、後がサブ")
        sp.add_argument("--main", help="メインの文言を上書きする")
        sp.add_argument("--sub", help="サブの文言を上書きする（空文字でサブなし）")
        sp.add_argument("--label", help="ラベルを上書きする（空文字でラベルなし）")

    p = sub.add_parser("prompt", help="送るプロンプトと見積もりを表示する（API は呼ばない）")
    common(p, generate=False)
    p.add_argument("--scene", help="写真の場面（英語2〜3文）")
    p.add_argument("--title-space", action="store_true", help="タイトルを載せる余地を残す")
    p.add_argument("--refs", type=int, default=0, help="参考画像を渡す前提で表示する（枚数）")
    title_args(p)
    p.set_defaults(func=cmd_prompt)

    g = sub.add_parser("photo", help="写真・素材を生成する（文字なし）")
    common(g)
    g.add_argument("--scene", required=True, help="写真の場面（英語2〜3文）")
    g.add_argument("--title-space", action="store_true", help="タイトルを載せる余地を残す（アイキャッチ用）")
    g.add_argument("--ref", action="append", default=[], help="トーンを合わせる参考画像（複数可）")
    g.set_defaults(func=cmd_photo)

    t = sub.add_parser("title", help="写真にタイトルを載せる（画像編集）")
    common(t)
    t.add_argument("--photo", required=True, help="タイトルを載せる写真")
    title_args(t)
    t.add_argument("--ref", help="文字デザインを揃える既存のアイキャッチ")
    t.set_defaults(func=cmd_title)

    k = sub.add_parser("cost", help="記録した費用を月別に集計する")
    k.add_argument("--cost-log", required=True)
    k.set_defaults(func=cmd_cost)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.cmd == "title" and not a.title and not a.main:
        build_parser().error("title には --title か --main が要る")
    try:
        a.func(a)
    except GahakuError as e:
        log(f"gahaku: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
