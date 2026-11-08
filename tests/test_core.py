import base64
import io
import json

import pytest
from PIL import Image

from gahaku import cli, pricing
from gahaku.config import GahakuError, load_design, parse_size, request_size
from gahaku.prompts import photo_prompt, title_prompt, title_text

DESIGN = {"style": "S", "constraints": "C", "sizes": {"og": "1200x630"},
          "title": {"label": "入門", "design": "D"}}


def test_request_size_keeps_valid_sizes():
    assert request_size(1200, 800) == (1200, 800)
    assert request_size(1536, 1024) == (1536, 1024)
    assert request_size(1920, 1080) == (1920, 1088)  # 1080 は 16 の倍数でない


def test_request_size_snaps_to_16():
    w, h = request_size(1200, 630)
    assert w % 16 == 0 and h % 16 == 0
    assert abs(w / h - 1200 / 630) < 0.02


def test_request_size_limits():
    w, h = request_size(7680, 4320)
    assert w <= 3840 and w * h <= 3840 * 2160
    w, h = request_size(400, 400)
    assert w * h >= 655_360 and w % 16 == 0
    with pytest.raises(GahakuError):
        request_size(4000, 1000)


def test_parse_size_names():
    assert parse_size("og", DESIGN) == (1200, 630)
    assert parse_size("1024x1536") == (1024, 1536)
    with pytest.raises(GahakuError):
        parse_size("big", DESIGN)


def test_title_text_split_and_label():
    assert title_text(DESIGN, "入門講座の費用｜内訳") == {"label": "入門", "main": "講座の費用", "sub": "内訳"}
    assert title_text(DESIGN, "A|B", label="") == {"label": "", "main": "A", "sub": "B"}
    assert title_text(DESIGN, "A｜B", sub="")["sub"] == ""


def test_prompts():
    p = photo_prompt(DESIGN, "a desk", (1200, 800), title_space=True, n_refs=1)
    assert "3:2 landscape" in p and "title" in p and "Reference images" in p
    t = title_prompt(DESIGN, {"label": "", "main": "費用", "sub": ""})
    assert '"費用" (2 characters)' in t and "Subtitle" not in t
    with pytest.raises(ValueError):
        title_prompt({"style": "S"}, {"label": "", "main": "x", "sub": ""})


def test_cost_and_snapshot_price():
    c = pricing.cost("gpt-image-2.5-flare-2026-09-08",
                     {"input_tokens_details": {"text_tokens": 1_000_000, "image_tokens": 0}, "output_tokens": 1_000_000})
    assert c["usd"] == pytest.approx(35.0)
    assert pricing.cost("unknown-model", {"output_tokens": 10})["usd"] is None


def test_load_design_requires_fields(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"style": "S"}))
    with pytest.raises(GahakuError):
        load_design(p)


def _png(w, h):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_photo_end_to_end_with_fake_api(tmp_path, monkeypatch, capsys):
    design = tmp_path / "d.json"
    design.write_text(json.dumps(DESIGN | {"size": "og"}))
    sent = {}

    def fake_generate(key, params):
        sent.update(params)
        return {"data": [{"b64_json": _png(1200, 624)}] * params["n"],
                "usage": {"input_tokens_details": {"text_tokens": 100, "image_tokens": 0}, "output_tokens": 5000}}

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr(cli.api, "generate", fake_generate)
    log = tmp_path / "cost.csv"
    cli.main(["photo", "--design", str(design), "--scene", "x", "--out", str(tmp_path / "a.webp"),
              "--n", "2", "--cost-log", str(log), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert sent["size"] == "1200x624" and sent["output_format"] == "webp"
    assert [Image.open(f).size for f in out["files"]] == [(1200, 630), (1200, 630)]
    assert out["files"][0].endswith("a-1.webp")
    assert pricing.estimate(log, "photo", out["model"], "1200x630", "high")[1] == 2
    assert pricing.estimate(log, "title", out["model"], "1200x630", "high") is None
