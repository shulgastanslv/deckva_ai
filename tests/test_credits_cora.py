"""Unit + e2e (mocked OpenRouter) tests."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app import credits
from app.catalog import get_model, list_models, quote_carousel_credits, resolve_model_id
from app.cora.plan import bind_content_to_plan, build_skeleton_plan, object_bindings
from app.main import app
from app.schemas import SlideContent


def test_catalog_acl():
    free = {m.model_id for m in list_models(plan="free")}
    assert "gemini-flash" in free
    assert "claude-sonnet" not in free
    starter = {m.model_id for m in list_models(plan="starter")}
    assert "claude-sonnet" in starter
    try:
        resolve_model_id("free", "claude-sonnet")
        assert False, "expected PermissionError"
    except PermissionError:
        pass
    assert resolve_model_id("free", None) == "gemini-flash"


def test_quote_formula():
    base = get_model("gemini-flash").base_credits
    assert quote_carousel_credits(model_id="gemini-flash", slides=7) == base
    assert quote_carousel_credits(model_id="gemini-flash", slides=10) == math.ceil(base * 10 / 7)


def test_hold_spend_refund():
    uid = "test_user_hold"
    credits.ensure_wallet(uid, plan="free")
    before = credits.balance_of(uid)["total"]
    q = credits.quote(model_id="gemini-flash", slides=7)["credits"]
    h = credits.hold(user_id=uid, generation_id="gen_1", amount=q)
    assert credits.balance_of(uid)["total"] == before - q
    credits.refund(h.id, reason="fail")
    assert credits.balance_of(uid)["total"] == before

    h2 = credits.hold(user_id=uid, generation_id="gen_2", amount=q)
    credits.spend(h2.id)
    assert credits.balance_of(uid)["total"] == before - q
    e = credits.spend(h2.id)
    assert e.generation_id == "gen_2"


def test_plan_objects():
    plan = build_skeleton_plan(
        cora_run_id="cor_test",
        mode="fast",
        topic="тема",
        language="ru",
        ratio="4:5",
        slides_count=5,
        model_id="gemini-flash",
    )
    assert plan["slidesCount"] == 5
    assert plan["jobs"][0]["tool"] == "llm.fill_and_layout"
    assert plan["slides"][0]["objects"][0]["id"] == "s0_headline"
    slides = [SlideContent(layout="cover", heading=f"H{i}", body=f"B{i}") for i in range(5)]
    slides[-1].layout = "cta"
    bound = bind_content_to_plan(plan, slides)
    assert bound["slides"][0]["objects"][0]["value"] == "H0"
    binds = object_bindings(bound)
    assert any(b["objectId"] == "s0_headline" for b in binds)


def _fake_carousel(n: int = 5) -> dict:
    layouts = ["cover", "statement", "tips", "results", "cta"]
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
                "image_prompt": "",
            }
            for i in range(n)
        ],
    }


def _fake_palette() -> dict:
    return {
        "name": "test_palette",
        "bg": "#FFFFFF",
        "text": "#111111",
        "muted": "#9A9A9A",
        "accent": "#F6C1C0",
        "accent_text": "#2A2A2A",
        "grid": "#CFCFCF",
        "photo": "#C8C8C8",
    }


def test_api_no_legacy_routes():
    c = TestClient(app)
    assert c.post("/generate", json={}).status_code == 404
    assert c.post("/palette", json={}).status_code == 404
    assert c.post("/text", json={}).status_code == 404


def test_cora_run_openrouter_path():
    c = TestClient(app)
    uid = "e2e_openrouter_user"
    before = c.get(f"/credits/wallet/{uid}?plan=free").json()["balance"]["total"]

    async def fake_chat_json(**kwargs):
        system = kwargs.get("system", "")
        if "палитр" in system.lower():
            return _fake_palette()
        return _fake_carousel(5)

    with patch("app.content.chat_json", new=AsyncMock(side_effect=fake_chat_json)), patch(
        "app.palette.chat_json", new=AsyncMock(side_effect=fake_chat_json)
    ):
        r = c.post(
            "/cora/run",
            json={
                "userId": uid,
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
    assert body["plan"]["jobs"][0]["tool"] == "llm.fill_and_layout"
    assert body["carousel"]["slides"]
    assert any(
        obj.get("coraObjectId")
        for slide in body["carousel"]["slides"]
        for obj in slide.get("objects", [])
    )
    after = c.get(f"/credits/wallet/{uid}?plan=free").json()["balance"]["total"]
    assert after == before - body["credits"]["spent"]

    got = c.get(f"/cora/runs/{body['coraRunId']}")
    assert got.status_code == 200
    assert got.json()["status"] == "done"


def test_cora_refund_without_key():
    c = TestClient(app)
    uid = "e2e_refund_user"
    before = c.get(f"/credits/wallet/{uid}?plan=free").json()["balance"]["total"]
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=False):
        # force require_api_key fail inside chat
        with patch("app.llm.openrouter_api_key", return_value=""):
            r = c.post(
                "/cora/run",
                json={
                    "userId": uid,
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
    after = c.get(f"/credits/wallet/{uid}?plan=free").json()["balance"]["total"]
    assert after == before


if __name__ == "__main__":
    test_catalog_acl()
    test_quote_formula()
    test_hold_spend_refund()
    test_plan_objects()
    test_api_no_legacy_routes()
    test_cora_run_openrouter_path()
    test_cora_refund_without_key()
    print("ok")
