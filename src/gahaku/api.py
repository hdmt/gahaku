"""OpenAI の画像 API（images/generations・images/edits）を呼ぶ。標準ライブラリだけで書く。"""

import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .config import GahakuError

BASE = "https://api.openai.com/v1/images"
TIMEOUT = 600  # 高品質・大きいサイズは数分かかることがある


def generate(key, params):
    body = json.dumps(params).encode()
    req = urllib.request.Request(f"{BASE}/generations", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    return _send(req, key)


def edit(key, params, images):
    """images の1枚目が編集の対象、2枚目以降は参考画像として渡る。"""
    boundary = uuid.uuid4().hex
    chunks = []
    for k, v in params.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for path in images:
        p = Path(path)
        if not p.exists():
            raise GahakuError(f"画像が無い: {path}")
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="{p.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n".encode()
        )
        chunks.append(p.read_bytes() + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"{BASE}/edits", data=b"".join(chunks), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    return _send(req, key)


def _send(req, key):
    req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise GahakuError(f"OpenAI API {e.code}: {e.read().decode(errors='replace')[:800]}") from e
    except urllib.error.URLError as e:
        raise GahakuError(f"OpenAI API に接続できない: {e.reason}") from e
    if not res.get("data"):
        raise GahakuError(f"画像が返ってこなかった: {json.dumps(res, ensure_ascii=False)[:800]}")
    return res
