"""画像 API に送るプロンプトを組み立てる。"""

from math import gcd


def _aspect(w, h):
    g = gcd(w, h)
    rw, rh = w // g, h // g
    if rw > 32 or rh > 32:  # 1366x768 のように約分しても大きいものは小数で書く
        return f"{w / h:.2f}:1"
    return f"{rw}:{rh}"


def _orientation(w, h):
    if w > h * 1.05:
        return "landscape"
    if h > w * 1.05:
        return "portrait"
    return "square"


def photo_prompt(cfg, scene, size, *, title_space=False, n_refs=0):
    """場面（scene）に、デザイン設定の画風と禁止事項を足す。

    この段階では文字を入れさせない。title_space のときも、文字の置き場所を
    「枠」として作らせない（別パネルのコラージュになりやすいため）。
    """
    w, h = size
    composition = (
        f"Composition: {_aspect(w, h)} {_orientation(w, h)} frame. "
        "One seamless image with consistent lighting across the entire frame."
    )
    if title_space:
        composition += (
            " Keep some calm, uncluttered background area that could later hold a title; "
            "do not draw any box, panel or border for it."
        )
    parts = [
        f"Scene: {scene}",
        composition,
        f"Style: {cfg['style']}",
        cfg.get("people", ""),
        "Reference images: match their color palette, lighting and overall tone. "
        "Do not copy their subjects, people, text or layout." if n_refs else "",
        f"Constraints: {cfg['constraints']}",
    ]
    return "\n\n".join(p for p in parts if p)


def title_text(cfg, title, main=None, sub=None, label=None):
    """タイトルを label / main / sub に分ける。｜（全角）か | の前がメイン、後がサブ。"""
    t = cfg.get("title", {})
    label = t.get("label", "") if label is None else label
    sep = "｜" if "｜" in title else "|"
    m, _, s = title.partition(sep)
    m = (main if main is not None else m).strip()
    s = (sub if sub is not None else s).strip()
    if label and m.startswith(label) and len(m) > len(label):
        m = m[len(label):].strip()  # ラベルと同じ語で始まるタイトルは重複させない
    return {"label": label, "main": m, "sub": s}


def title_prompt(cfg, text, *, has_ref=False):
    design = cfg.get("title", {}).get("design")
    if not design:
        raise ValueError("デザイン設定に title.design が無い")
    lines = [("Small label", text["label"]), ("Main title (largest)", text["main"]), ("Subtitle", text["sub"])]
    spec = "\n".join(f'- {name}: "{v}" ({len(v)} characters)' for name, v in lines if v)
    parts = [
        "Edit the first image into a blog eyecatch by adding the Japanese title below. "
        "Keep the photo itself (people, objects, background, lighting) unchanged; only add the title design.",
        "Text to render. Copy each string exactly, character by character. "
        "Do not translate, paraphrase, add, omit, or reorder characters. "
        "The straight double quotes around each string are delimiters only; do not render them. "
        "Japanese corner brackets 「」 inside a string are part of the text and must be rendered.\n" + spec,
        f"Title design: {design}",
        "Choose the line breaks for the main title yourself, but never break inside a word. "
        "All text must be fully inside the frame, crisp, and readable at small sizes.",
        "The second image is an existing eyecatch from the same site. Match its title design "
        "(typeface, colors, panel, placement), not its text or photo." if has_ref else "",
        "Constraints: Render only the text listed above. Japanese characters must be correct and complete, "
        "with no missing or extra strokes. No other text, logos, watermarks, or symbols.",
    ]
    return "\n\n".join(p for p in parts if p)
