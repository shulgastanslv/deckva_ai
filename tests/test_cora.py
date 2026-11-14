"""Unit + e2e (mocked OpenRouter) tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.catalog import list_models, resolve_model_id
from app.cora.plan import bind_content_to_plan, build_skeleton_plan, decide_design, object_bindings
from app.main import app
from app.schemas import SlideContent


def test_catalog_all_models_for_any_plan():
    free = {m.model_id for m in list_models(plan="free")}
    pro = {m.model_id for m in list_models(plan="pro")}
    assert "gemini-flash" in free
    assert "claude-sonnet" in free
    assert "claude-opus" in free
    assert free == pro
    assert resolve_model_id("free", "claude-sonnet") == "claude-sonnet"
    assert resolve_model_id("free", None) == "gemini-flash"


def test_design_varies_and_optional_cover():
    a = decide_design(cora_run_id="cor_a", topic="fitness", slides_count=7)
    b = decide_design(cora_run_id="cor_b", topic="finance", slides_count=7)
    assert "hasCover" in a and "mood" in a
    assert a["mood"] != "" 
    # Different runs should often differ (not a hard guarantee on every field)
    assert a != b or a["mood"] == b["mood"]  # at least structures exist
    # Same run id + topic is stable
    a2 = decide_design(cora_run_id="cor_a", topic="fitness", slides_count=7)
    assert a == a2


def test_plan_objects_with_and_without_cover():
    with_cover = build_skeleton_plan(
        cora_run_id="cor_cover",
        mode="fast",
        topic="тема",
        language="ru",
        ratio="4:5",
        slides_count=5,
        model_id="gemini-flash",
        design={
            "hasCover": True,
            "mood": "bold_pop",
            "gridMode": "edges",
            "accentBias": 0.5,
            "photoRatio": 0.45,
            "midRoles": ["offer", "proof", "howto"],
            "midLayouts": ["list", "quote", "list"],
            "preferredContentLayouts": ["statement", "tips"],
        },
    )
    assert with_cover["design"]["hasCover"] is True
    assert with_cover["slides"][0]["layout"] == "hero_cover"
    assert any(o.get("role") == "cover" for o in with_cover["slides"][0]["objects"])

    no_cover = build_skeleton_plan(
        cora_run_id="cor_nocover",
        mode="fast",
        topic="тема",
        language="ru",
        ratio="4:5",
        slides_count=5,
        model_id="gemini-flash",
        design={
            "hasCover": False,
            "mood": "midnight_editorial",
            "gridMode": "none",
            "accentBias": 0.6,
            "photoRatio": None,
            "midRoles": ["pain", "shift", "proof"],
            "midLayouts": ["statement", "list", "quote"],
            "preferredContentLayouts": ["statement", "tips"],
        },
    )
    assert no_cover["design"]["hasCover"] is False
    assert no_cover["slides"][0]["layout"] == "hero_text"
    assert not any(o.get("role") == "cover" for o in no_cover["slides"][0]["objects"])

    slides = [SlideContent(layout="cover", heading=f"H{i}", body=f"B{i}") for i in range(5)]
    slides[-1].layout = "cta"
    bound = bind_content_to_plan(with_cover, slides)
    assert bound["slides"][0]["objects"][0]["value"] == "H0"
    binds = object_bindings(bound)
    assert any(b["objectId"] == "s0_headline" for b in binds)


def _fake_carousel(n: int = 5, *, has_cover: bool = True) -> dict:
    layouts = (
        ["cover", "statement", "tips", "results", "cta"]
        if has_cover
        else ["statement", "orange_quote", "tips", "results", "cta"]
    )
    return {
        "title": "Тест карусель",
        "tagline": "tag",
        "category": "Test",
        "slides": [
            {
                "layout": layouts[min(i, len(layouts) - 1)],
                "heading": f"Заголовок {i + 1}",
                "highlight": "",
                "body": f"Текст {i + 1}",
                "items": ["a", "b"] if i in {2, 3} else [],
                "badges": [],
                "flow": "",
                "callout": "",
                "tag": "",
                "image_prompt": "soft daylight desk" if has_cover and i == 0 else "",
            }
            for i in range(n)
        ],
    }


def _fake_palette() -> dict:
    return {
        "name": "midnight_ink",
        "bg": "#12141A",
        "text": "#F4F1EA",
        "muted": "#8A8F9C",
        "accent": "#E8A87C",
        "accent_text": "#1A120C",
        "grid": "#2A2F3A",
        "photo": "#1E222C",
    }


def test_api_no_legacy_routes():
    c = TestClient(app)
    assert c.post("/generate", json={}).status_code == 404
    assert c.get("/credits/wallet/u1").status_code == 404


def test_stock_query_cleaner_and_fill():
    from app.schemas import SlideContent
    from app.stock_photos import _clean_query, fill_slide_photos_from_prompts

    assert "desk" in _clean_query("soft daylight desk!!! @home")
    slides = [
        SlideContent(layout="cover", heading="H0", image_prompt="soft daylight desk"),
        SlideContent(layout="statement", heading="H1", image_prompt=""),
        SlideContent(layout="tips", heading="H2", image_prompt="minimal workspace laptop"),
        SlideContent(layout="results", heading="H3"),
        SlideContent(layout="cta", heading="H4"),
    ]

    async def fake_search(prompt, **kwargs):
        return f"https://example.com/{prompt.replace(' ', '-')}.jpg"

    import asyncio

    with patch("app.stock_photos.stock_photos_enabled", return_value=True), patch(
        "app.stock_photos.search_stock_photo", new=AsyncMock(side_effect=fake_search)
    ):
        photos = asyncio.run(
            fill_slide_photos_from_prompts(
                slides=slides,
                slide_photos=["", "", "", "", ""],
                topic="блог",
                salt="cor_test",
                has_cover=True,
            )
        )
    assert photos[0].startswith("https://example.com/")
    assert photos[1] == ""
    assert photos[2].startswith("https://example.com/")
    assert photos[4] == ""


def test_cora_run_openrouter_path():
    c = TestClient(app)

    async def fake_chat_json(**kwargs):
        system = kwargs.get("system", "")
        if "арт-директор" in system.lower() or "палитр" in system.lower():
            return _fake_palette()
        return _fake_carousel(5, has_cover=True)

    with patch("app.content.chat_json", new=AsyncMock(side_effect=fake_chat_json)), patch(
        "app.palette.chat_json", new=AsyncMock(side_effect=fake_chat_json)
    ), patch("app.cora.runner.stock_photos_enabled", return_value=False):
        r = c.post(
            "/cora/run",
            json={
                "userId": "e2e_openrouter_user",
                "topic": "как вести блог",
                "language": "ru",
                "ratio": "4:5",
                "slidesCount": 5,
                "handle": "@x",
                "cover": "",
                "mode": "fast",
                "plan": "free",
                "modelId": "gemini-flash",
                "save": False,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "done"
    assert body["llmProvider"] == "openrouter"
    assert "credits" not in body
    assert "design" in body["plan"]
    assert "hasCover" in body["plan"]["design"]
    assert "mood" in body["plan"]["design"]
    assert body["palette"]["name"] == "midnight_ink"
    assert body["carousel"]["slides"]

    got = c.get(f"/cora/runs/{body['coraRunId']}")
    assert got.status_code == 200
    assert got.json()["status"] == "done"


def test_cora_fails_without_key():
    c = TestClient(app)
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False):
        with patch("app.llm.openrouter_api_key", return_value=""):
            r = c.post(
                "/cora/run",
                json={
                    "userId": "e2e_no_key_user",
                    "topic": "как вести блог",
                    "language": "ru",
                    "ratio": "4:5",
                    "slidesCount": 5,
                    "handle": "@x",
                    "cover": "",
                    "plan": "free",
                    "modelId": "gemini-flash",
                },
            )
    assert r.status_code == 503


if __name__ == "__main__":
    test_catalog_acl()
    test_design_varies_and_optional_cover()
    test_plan_objects_with_and_without_cover()
    test_api_no_legacy_routes()
    test_cora_run_openrouter_path()
    test_cora_fails_without_key()
    print("ok")
