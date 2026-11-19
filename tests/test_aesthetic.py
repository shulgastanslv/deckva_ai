"""Tests for CORA aesthetic (Pinterest LLM) branch."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.cora.aesthetic.assemble import render_aesthetic_slide
from app.cora.aesthetic.generate import parse_aesthetic_raw, to_slide_contents
from app.cora.plan import decide_design
from app.fonts import Typography
from app.main import app
from app.palette import Palette


def _aesthetic_payload(n: int = 4) -> dict:
    slides = []
    for i in range(n):
        if i == 0:
            elements = [
                {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 1, "slot": 0},
                {"kind": "scrim", "x": 0, "y": 0, "w": 1, "h": 1, "opacity": 0.2},
                {
                    "kind": "heading",
                    "x": 0.08,
                    "y": 0.1,
                    "w": 0.84,
                    "h": 0.4,
                    "case": "lower",
                    "size": "hero",
                    "stack": True,
                    "color": "#F2E6A8",
                },
                {"kind": "pill", "x": 0.08, "y": 0.6, "w": 0.35, "h": 0.05, "text": "MOSCOW", "icon": "pin"},
                {"kind": "handle", "x": 0.08, "y": 0.04, "w": 0.3, "h": 0.04, "color": "#FFFFFF"},
            ]
            prompts = ["person hoodie crosswalk overhead urban"]
        elif i == n - 1:
            elements = [
                {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 1, "slot": 0},
                {
                    "kind": "heading",
                    "x": 0.1,
                    "y": 0.4,
                    "w": 0.8,
                    "align": "center",
                    "size": "display",
                    "case": "lower",
                    "color": "#F2E6A8",
                },
            ]
            prompts = ["soft morning coffee flat lay"]
        else:
            elements = [
                {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 0.5, "slot": 0},
                {"kind": "photo", "x": 0, "y": 0.5, "w": 1, "h": 0.5, "slot": 1},
                {
                    "kind": "heading",
                    "x": 0.08,
                    "y": 0.12,
                    "w": 0.7,
                    "size": "display",
                    "color": "#FFFFFF",
                },
                {
                    "kind": "handle",
                    "x": 0.35,
                    "y": 0.47,
                    "w": 0.3,
                    "style": "pill",
                    "size": "meta",
                },
            ]
            prompts = ["latte art top down floral cloth", "woman drinking iced coffee indoor"]
        slides.append(
            {
                "heading": f"слайд идея {i + 1}",
                "body": "короткий совет" if i else "one day soft ritual",
                "badges": ["AUTUMN", "18/JUN"],
                "callout": "чтобы влюбиться" if i == 0 else "",
                "footer": "блог про карусели",
                "image_prompts": prompts,
                "elements": elements,
            }
        )
    return {
        "title": "Осень в городе",
        "tagline": "тихий ритуал",
        "category": "Lifestyle",
        "moodHint": "warm cream burgundy editorial",
        "slides": slides,
    }


def test_decide_design_aesthetic_engine():
    d = decide_design(
        cora_run_id="cor_ae",
        topic="осень",
        slides_count=6,
        skill_id="aesthetic",
    )
    assert d["engine"] == "aesthetic_llm"
    assert d["mood"] == "pinterest_editorial"
    assert d["skillId"] == "aesthetic"
    assert d["gridMode"] == "none"


def test_parse_and_render_aesthetic():
    parsed = parse_aesthetic_raw(_aesthetic_payload(4), 4)
    assert len(parsed["slides"]) == 4
    assert parsed["slides"][0]["elements"]
    assert any(e["kind"] == "photo" for e in parsed["slides"][1]["elements"])
    slides = to_slide_contents(parsed)
    assert slides[0].layout == "cover"
    assert slides[-1].layout == "cta"

    palette = Palette(
        name="test",
        bg="#111111",
        text="#F5F5F5",
        muted="#999999",
        accent="#E8A87C",
        accent_text="#111111",
        grid="#333333",
        photo="#222222",
    )
    typo = Typography(
        font_family="Poppins",
        type_scale="editorial",
        head_size=60,
        body_size=22,
        meta_size=16,
        show_handle=True,
    )
    fabric = render_aesthetic_slide(
        parsed["slides"][0],
        index=0,
        slides_count=4,
        width=1080,
        height=1350,
        handle="@sasha",
        palette=palette,
        typography=typo,
        photos=["data:image/png;base64,aaa"],
    )
    types = {o["type"] for o in fabric["objects"]}
    assert "Image" in types
    assert "Textbox" in types
    assert any(o.get("swibpStyle") == "heading" for o in fabric["objects"])


def test_cora_run_aesthetic_path():
    c = TestClient(app)

    async def fake_chat_json(**kwargs):
        system = kwargs.get("system", "")
        low = system.lower()
        if "pinterest" in low or "aesthetic" in low or "elements" in system:
            return _aesthetic_payload(4)
        if "типографик" in low or "fontFamily" in system:
            return {
                "fontFamily": "Poppins",
                "typeScale": "editorial",
                "headSize": 64,
                "bodySize": 24,
                "metaSize": 18,
            }
        if "арт-директор" in low or "палитр" in low:
            return {
                "name": "cream_editorial",
                "bg": "#1A1612",
                "text": "#F2E6A8",
                "muted": "#A89880",
                "accent": "#C4A574",
                "accent_text": "#1A1612",
                "grid": "#3A3228",
                "photo": "#2A241C",
            }
        return _aesthetic_payload(4)

    with patch("app.cora.aesthetic.generate.chat_json", new=AsyncMock(side_effect=fake_chat_json)), patch(
        "app.palette.chat_json", new=AsyncMock(side_effect=fake_chat_json)
    ), patch(
        "app.fonts.chat_json", new=AsyncMock(side_effect=fake_chat_json)
    ), patch(
        "app.cora.aesthetic.photos.stock_photos_enabled", return_value=False
    ), patch(
        "app.cora.runner.stock_photos_enabled", return_value=False
    ):
        r = c.post(
            "/cora/run",
            json={
                "userId": "e2e_aesthetic",
                "topic": "один день из жизни стилиста осенью",
                "language": "ru",
                "ratio": "4:5",
                "slidesCount": 4,
                "handle": "@sasha",
                "showHandle": True,
                "skillId": "aesthetic",
                "cover": "",
                "modelId": "gemini-flash",
                "stockPhotos": False,
                "save": False,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "done"
    assert body["plan"]["design"]["engine"] == "aesthetic_llm"
    assert body["plan"]["design"]["templateId"] == "aesthetic_llm" or body["carousel"].get(
        "templateId"
    ) == "aesthetic_llm"
    assert body["carousel"]["slides"]
    # stacked / free layout produced textboxes without requiring classic template footer
    objs = body["carousel"]["slides"][0]["objects"]
    assert any(o.get("type") == "Textbox" for o in objs)


if __name__ == "__main__":
    test_decide_design_aesthetic_engine()
    test_parse_and_render_aesthetic()
    test_cora_run_aesthetic_path()
    print("ok")
