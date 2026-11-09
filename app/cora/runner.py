"""CORA Fast: intake → plan → execute → assemble + credits."""

from __future__ import annotations

import uuid
from typing import Any

from app import credits
from app.catalog import PlanId, resolve_model_id
from app.content import fill_and_layout, normalize_slides
from app.cora.assemble import assemble_carousel, content_from_raw
from app.cora.plan import bind_content_to_plan, build_skeleton_plan, object_bindings
from app.cora.store import save_run
from app.cover_media import resolve_cover_src
from app.palette import generate_palette
from app.schemas import CoraRunRequest, CoraRunResponse, CreditsInfo

LLM_PROVIDER = "openrouter"


def _new_run_id() -> str:
    return f"cor_{uuid.uuid4().hex[:14]}"


def _brand_dict(req: CoraRunRequest) -> dict[str, Any]:
    if not req.brand_kit:
        return {}
    raw = {
        "palette": req.brand_kit.palette,
        "fonts": req.brand_kit.fonts,
        "voice": req.brand_kit.voice,
        "logoAssetId": req.brand_kit.logo_asset_id,
    }
    return {k: v for k, v in raw.items() if v}


async def run_cora_fast(req: CoraRunRequest) -> CoraRunResponse:
    plan_id: PlanId = req.plan  # type: ignore[assignment]
    credits.ensure_wallet(req.user_id, plan=plan_id)

    try:
        model_id = resolve_model_id(plan_id, req.model_id)
    except PermissionError as exc:
        raise RuntimeError(str(exc)) from exc

    mode = "fast" if req.mode != "fast" else req.mode  # Thinking = phase B
    slides_count = max(4, min(10, req.slides_count))
    quote = credits.quote(model_id=model_id, slides=slides_count, mode=mode)
    cora_run_id = _new_run_id()
    provider = LLM_PROVIDER

    hold_row = credits.hold(
        user_id=req.user_id,
        generation_id=cora_run_id,
        amount=quote["credits"],
    )
    hold_id = hold_row.id
    status = "planning"

    base_record: dict[str, Any] = {
        "coraRunId": cora_run_id,
        "userId": req.user_id,
        "status": status,
        "mode": mode,
        "modelId": model_id,
        "intake": req.model_dump(by_alias=True),
        "holdId": hold_id,
        "llmProvider": provider,
    }
    save_run(base_record)

    try:
        plan = build_skeleton_plan(
            cora_run_id=cora_run_id,
            mode=mode,
            topic=req.topic,
            language=req.language,
            ratio=req.ratio,
            slides_count=slides_count,
            model_id=model_id,
            brand=_brand_dict(req),
            seed_text=req.seed_text,
        )
        save_run({**base_record, "status": "planning", "plan": plan})

        status = "executing"
        save_run({**base_record, "status": status, "plan": plan})

        cover_src = await resolve_cover_src(req.cover)
        topic_for_llm = req.topic
        if req.seed_text:
            topic_for_llm = f"{req.topic}\n\nSource copy:\n{req.seed_text}"

        raw = await fill_and_layout(
            topic=topic_for_llm,
            slides_count=slides_count,
            language=req.language,
            handle=req.handle,
            model_id=model_id,
            plan=plan,
        )
        slides = await normalize_slides(
            raw,
            topic=topic_for_llm,
            slides_count=slides_count,
            language=req.language,
            handle=req.handle,
            model_id=model_id,
        )
        content = content_from_raw(
            raw=raw,
            slides=slides,
            handle=req.handle,
            cover_src=cover_src,
        )
        palette = await generate_palette(
            topic=req.topic,
            language=req.language,
            model_id=model_id,
        )

        status = "assembling"
        plan = bind_content_to_plan(plan, slides)
        assembled = assemble_carousel(
            content=content,
            ratio=req.ratio,
            palette=palette,
            plan=plan,
            cora_run_id=cora_run_id,
            save=req.save,
        )

        spend_entry = credits.spend(hold_id)
        status = "done"
        response = CoraRunResponse(
            coraRunId=cora_run_id,
            status=status,
            mode=mode,  # type: ignore[arg-type]
            modelId=model_id,
            plan=plan,
            objectBindings=object_bindings(plan),
            title=assembled["title"],
            aspectRatio=assembled["aspectRatio"],
            width=assembled["width"],
            height=assembled["height"],
            path=assembled.get("path"),
            palette=assembled["palette"],
            carousel=assembled["carousel"],
            credits=CreditsInfo(
                quoted=quote["credits"],
                spent=spend_entry.amount,
                holdId=hold_id,
                spendLedgerId=spend_entry.id,
                refunded=False,
                wallet=credits.balance_of(req.user_id),
            ),
            llmProvider=provider,
        )
        save_run(
            {
                **base_record,
                **response.model_dump(),
                "status": "done",
                "spendLedgerIds": [spend_entry.id],
            }
        )
        return response
    except Exception as exc:
        try:
            credits.refund(hold_id, reason=str(exc)[:240])
        except Exception:  # noqa: BLE001
            pass
        err = f"CORA failed ({status}): {exc}"
        save_run(
            {
                **base_record,
                "status": "failed",
                "error": err,
                "credits": {
                    "quoted": quote["credits"],
                    "spent": None,
                    "holdId": hold_id,
                    "refunded": True,
                    "wallet": credits.balance_of(req.user_id),
                },
            }
        )
        raise RuntimeError(err) from exc
