"""Unit tests for catalog + credits + plan scaffolding (no OpenRouter)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.catalog import get_model, list_models, quote_carousel_credits, resolve_model_id
from app.cora.plan import bind_content_to_plan, build_skeleton_plan, object_bindings
from app.schemas import SlideContent
from app import credits


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
    # idempotent spend
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
    slides = [
        SlideContent(layout="cover", heading=f"H{i}", body=f"B{i}")
        for i in range(5)
    ]
    slides[-1].layout = "cta"
    bound = bind_content_to_plan(plan, slides)
    assert bound["slides"][0]["objects"][0]["value"] == "H0"
    binds = object_bindings(bound)
    assert any(b["objectId"] == "s0_headline" for b in binds)


if __name__ == "__main__":
    test_catalog_acl()
    test_quote_formula()
    test_hold_spend_refund()
    test_plan_objects()
    print("ok")
