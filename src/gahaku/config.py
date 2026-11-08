"""デザイン設定・APIキー・サイズの扱い。"""

import json
import math
import os
import re
from pathlib import Path

DEFAULT_MODEL = "gpt-image-2.5-sunburst"
DEFAULT_QUALITY = "high"
ENV_FILE = Path.home() / ".config" / "gahaku" / ".env"

# gpt-image-2 以降のサイズ指定の制約（API リファレンスより）。
# 幅・高さは 16 の倍数、縦横比は 1:3〜3:1、最大 3840x2160。
# 下限ははっきり書かれていないため、小さいサイズは大きめに生成して縮小する。
MAX_EDGE = 3840
MAX_PIXELS = 3840 * 2160
MIN_PIXELS = 655_360


class GahakuError(Exception):
    """利用者に見せるエラー。"""


def load_design(path):
    p = Path(path)
    if not p.exists():
        raise GahakuError(f"デザイン設定が無い: {path}")
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GahakuError(f"{path} の JSON が読めない: {e}") from e
    for key in ("style", "constraints"):
        if not cfg.get(key):
            raise GahakuError(f"{path} に {key} が無い")
    cfg.setdefault("model", DEFAULT_MODEL)
    cfg.setdefault("quality", DEFAULT_QUALITY)
    return cfg


def api_key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() == "OPENAI_API_KEY" and v.strip():
                return v.strip().strip('"').strip("'")
    raise GahakuError(f"OPENAI_API_KEY が無い。環境変数か {ENV_FILE} に設定する")


def parse_size(value, cfg=None):
    """'1200x800' か、デザイン設定の sizes に書いた名前（'eyecatch' など）を (幅, 高さ) にする。"""
    sizes = (cfg or {}).get("sizes", {})
    raw = sizes.get(value, value)
    m = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", str(raw))
    if not m:
        names = "、".join(sizes) or "なし"
        raise GahakuError(f"サイズが読めない: {value}（WIDTHxHEIGHT か、sizes の名前: {names}）")
    w, h = int(m.group(1)), int(m.group(2))
    if w <= 0 or h <= 0:
        raise GahakuError(f"サイズが不正: {value}")
    return w, h


def default_size(cfg):
    if cfg.get("size"):
        return parse_size(cfg["size"], cfg)
    raise GahakuError("--size を指定するか、デザイン設定に size を書く")


def request_size(w, h):
    """仕上がりサイズから、API に頼むサイズを決める。

    条件を満たすサイズ（1200x800 など）はそのまま頼む。満たさないときは
    縦横比を保ったまま 16 の倍数に寄せ、保存時に切り抜き・縮小で仕上がりサイズにする。
    """
    ratio = w / h
    if not (1 / 3 <= ratio <= 3):
        raise GahakuError(f"縦横比が 1:3〜3:1 の外にある: {w}x{h}")
    px = w * h
    scale = 1.0
    if px > MAX_PIXELS:
        scale = math.sqrt(MAX_PIXELS / px)
    elif px < MIN_PIXELS:
        scale = math.sqrt(MIN_PIXELS / px)
    if max(w, h) * scale > MAX_EDGE:
        scale = MAX_EDGE / max(w, h)

    if scale < 1:
        def snap(v):
            return max(16, math.floor(v * scale / 16) * 16)
    elif scale > 1:
        def snap(v):
            return math.ceil(v * scale / 16) * 16
    else:
        def snap(v):
            return max(16, round(v / 16) * 16)
    return snap(w), snap(h)
