"""料金表とコストの記録。

OpenAI の画像モデルはトークン課金（USD / 100万トークン、Standard）。
料金が変わったら PRICES と PRICES_CHECKED を直す。
"""

import csv
import datetime
import os
import re
from pathlib import Path

PRICES_CHECKED = "2026-11-08"
PRICES_SOURCE = "https://developers.openai.com/api/docs/pricing"

PRICES = {
    "gpt-image-2.6-sunburst": {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00},
    "gpt-image-2.6-flare": {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00},
    "gpt-image-2.5-sunburst": {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00},
    "gpt-image-2.5-flare": {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00},
    "gpt-image-2": {"text_in": 5.00, "image_in": 8.00, "image_out": 30.00},
    "gpt-image-1.5": {"text_in": 5.00, "image_in": 8.00, "image_out": 32.00},
    "gpt-image-1-mini": {"text_in": 2.00, "image_in": 2.50, "image_out": 8.00},
}

USD_JPY = float(os.environ.get("USD_JPY", 150))  # 円換算の目安

LOG_FIELDS = ["at", "stage", "model", "size", "quality", "out",
              "text_in", "image_in", "image_out", "usd"]


def price(model):
    """スナップショット名（gpt-image-2.5-flare-2026-09-08 など）は日付を外して引く。"""
    base = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model)
    return PRICES.get(base)


def cost(model, usage):
    """API が返した usage から実費を出す。料金表に無いモデルは usd=None。"""
    details = usage.get("input_tokens_details") or {}
    text_in = details.get("text_tokens", 0)
    image_in = details.get("image_tokens", 0)
    if not details and usage.get("input_tokens"):
        text_in = usage["input_tokens"]
    image_out = usage.get("output_tokens", 0)
    p = price(model)
    usd = None
    if p:
        usd = (text_in * p["text_in"] + image_in * p["image_in"] + image_out * p["image_out"]) / 1e6
    return {"text_in": text_in, "image_in": image_in, "image_out": image_out, "usd": usd}


def fmt(usd):
    if usd is None:
        return "不明（料金表に無いモデル）"
    return f"${usd:.3f}（約{usd * USD_JPY:.0f}円）"


def log_rows(path, rows):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _read(path):
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def estimate(path, stage, model, size, quality):
    """記録から、同じ段階・モデル・サイズ・品質の1枚あたりの平均を出す。記録が無ければ None。

    title は写真を入力に渡す分だけ photo より高いので、段階も揃える。
    """
    usds = [float(r["usd"]) for r in _read(path) if path and r.get("usd") and r["stage"] == stage
            and r["model"] == model and r["size"] == size and r["quality"] == quality]
    if not usds:
        return None
    return sum(usds) / len(usds), len(usds)


def monthly(path):
    months = {}
    for r in _read(path):
        m = months.setdefault(r["at"][:7], [0, 0.0])
        m[0] += 1
        m[1] += float(r["usd"] or 0)
    return dict(sorted(months.items()))
