"""CORA Fast: intake → plan → execute → assemble + credits hold/spend/refund."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from app import credits
from app.catalog import PlanId, resolve_model_id
from app.content import (
    generate_carousel_raw,
    normalize_slides,
    require_category,
    require_str,
)
from app.cora.plan import bind_content_to_plan, build_skeleton_plan, object_bindings
from app.cover_media import resolve_cover_src
from app.generator import _palette_response, _slug
from app.palette import generate_palette
from app.schemas import CarouselContent, CoraRunRequest
from app.template import build_carousel

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def _new_run_id() -> str:
    return f"cor_{uuid.uuid4().hex[:14]}"


async def run_cora_fast(req: CoraRunRequest) -> dict[str, Any]:
    plan_id: PlanId = req.plan  # type: ignore[assignment]
    credits.ensure_wallet(req.user_id, plan=plan_id)

    try:
        model_id = resolve_model_id(plan_id, req.model_id)
    except PermissionError as exc:
        raise RuntimeError(str(exc)) from exc

    mode = req.mode
    if mode != "fast":
        # Phase A: Thinking not implemented — fall back to fast billing/path.
        mode = "fast"

    slides_count = max(4, min(10, req.slides_count))
    quote = credits.quote(model_id=model_id, slides=slides_count, mode=mode)
    cora_run_id = _new_run_id()
    generation_id = cora_run_id

    try:
        hold_row = credits.hold(
            user_id=req.user_id,
            generation_id=generation_id,
            amount=quote["credits"],
        )
    except RuntimeError:
        raise

    status = "planning"
    plan: dict[str, Any] | None = None
    hold_id = hold_row.id

    try:
        brand = None
        if req.brand_kit:
            brand = {
                "palette": req.brand_kit.palette,
                "fonts": req.brand_kit.fonts,
                "voice": req.brand_kit.voice,
                "logoAssetId": req.brand_kit.logo_asset_id,
            }

        plan = build_skeleton_plan(
            cora_run_id=cora_run_id,
            mode=mode,
            topic=req.topic,
            language=req.language,
            ratio=req.ratio,
            slides_count=slides_count,
            model_id=model_id,
            brand={k: v for k, v in (brand or {}).items() if v},
            seed_text=req.seed_text,
        )

        status = "executing"
        cover_src = await resolve_cover_src(req.cover)

        topic_for_llm = req.topic
        if req.seed_text:
            topic_for_llm = f"{req.topic}\n\nSource copy:\n{req.seed_text}"

        raw = await generate_carousel_raw(
            topic=topic_for_llm,
            slides_count=slides_count,
            language=req.language,
            handle=req.handle,
            model_id=model_id,
        )
        slides = await normalize_slides(
            raw,
            topic=topic_for_llm,
            slides_count=slides_count,
            language=req.language,
            handle=req.handle,
            model_id=model_id,
        )
        content = CarouselContent(
            title=require_str(raw.get("title"), "title"),
            tagline=str(raw.get("tagline", "")).strip(),
            handle=req.handle,
            category=require_category(raw.get("category")),
            cover=cover_src,
            slides=slides,
        )

        palette = await generate_palette(
            topic=req.topic,
            language=req.language,
            model_id=model_id,
        )

        status = "assembling"
        seed = int(time.time() * 1000) % 2_147_483_647
        carousel = build_carousel(
            content,
            aspect_ratio=req.ratio,
            palette=palette,
            seed=seed,
        )
        plan = bind_content_to_plan(plan, slides)

        path: str | None = None
        if req.save:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out = OUTPUT_DIR / f"{int(time.time())}_{_slug(content.title)}.json"
            public = {
                "coraRunId": cora_run_id,
                "title": carousel["title"],
                "aspectRatio": carousel["aspectRatio"],
                "width": carousel["width"],
                "height": carousel["height"],
                "palette": palette.to_dict(),
                "plan": plan,
                "slides": carousel["slides"],
            }
            out.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
            path = str(out)

        spend_entry = credits.spend(hold_id)
        status = "done"

        return {
            "coraRunId": cora_run_id,
            "status": status,
            "mode": mode,
            "modelId": model_id,
            "plan": plan,
            "objectBindings": object_bindings(plan),
            "title": content.title,
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "path": path,
            "palette": _palette_response(palette),
            "carousel": {
                "title": carousel["title"],
                "aspectRatio": carousel["aspectRatio"],
                "width": carousel["width"],
                "height": carousel["height"],
                "slides": carousel["slides"],
            },
            "credits": {
                "quoted": quote["credits"],
                "spent": spend_entry.amount,
                "holdId": hold_id,
                "spendLedgerId": spend_entry.id,
                "wallet": credits.balance_of(req.user_id),
            },
        }
    except Exception as exc:
        try:
            credits.refund(hold_id, reason=str(exc)[:240])
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError(f"CORA failed ({status}): {exc}") from exc
