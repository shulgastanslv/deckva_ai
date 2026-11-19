"""CORA Fast: intake → plan → execute → assemble."""

from __future__ import annotations

import uuid
from typing import Any

from app.catalog import resolve_model_id
from app.content import fill_and_layout, normalize_slides
from app.cora.assemble import assemble_carousel, content_from_raw
from app.cora.plan import bind_content_to_plan, build_skeleton_plan, decide_design, object_bindings
from app.cora.skills import normalize_skill_id, skill_prompt_brief
from app.cora.store import save_run
from app.cover_media import resolve_cover_src
from app.fonts import generate_typography, resolve_font
from app.palette import generate_palette
from app.schemas import CoraRunRequest, CoraRunResponse
from app.stock_photos import fill_slide_photos_from_prompts, stock_photos_enabled

async def _resolve_images(req: CoraRunRequest) -> list[str]:
    """Cover + image attachments → data URLs (cover first when present)."""
    out: list[str] = []
    seen: set[str] = set()

    async def add(raw: str | None) -> None:
        src = (raw or "").strip()
        if not src or src in seen:
            return
        resolved = await resolve_cover_src(src)
        if not resolved or resolved in seen:
            return
        seen.add(src)
        seen.add(resolved)
        out.append(resolved)

    cover_role = next(
        (
            a
            for a in req.attachments
            if a.kind == "image" and (a.role or "").lower() == "cover" and (a.data_url or "").strip()
        ),
        None,
    )
    if cover_role:
        await add(cover_role.data_url)
    elif (req.cover or "").strip():
        await add(req.cover)

    for att in req.attachments:
        if att.kind != "image":
            continue
        await add(att.data_url)
    return out


def _seed_from_attachments(req: CoraRunRequest) -> str:
    chunks: list[str] = []
    if (req.seed_text or "").strip():
        chunks.append(req.seed_text.strip())
    for att in req.attachments:
        if att.kind != "text":
            continue
        body = (att.text or "").strip()
        if not body:
            continue
        name = (att.name or "note").strip() or "note"
        chunks.append(f"Attached “{name}”: {body}")
    return "\n\n".join(chunks)[:8000]


def _assign_slide_photos(
    *,
    images: list[str],
    slides_count: int,
    has_cover: bool,
) -> list[str]:
    """Map images onto slide indexes: [0]=cover, then mid slides, never CTA."""
    photos = [""] * slides_count
    if not images:
        return photos
    if has_cover:
        photos[0] = images[0]
        extras = images[1:]
    else:
        extras = images
    mid = list(range(1, max(1, slides_count - 1)))
    for i, src in enumerate(extras):
        if i >= len(mid):
            break
        photos[mid[i]] = src
    return photos

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
    try:
        model_id = resolve_model_id(req.model_id)
    except PermissionError as exc:
        raise RuntimeError(str(exc)) from exc

    mode = "fast" if req.mode != "fast" else req.mode  # Thinking = phase B
    slides_count = max(1, min(10, req.slides_count))
    cora_run_id = _new_run_id()
    provider = LLM_PROVIDER
    status = "planning"

    base_record: dict[str, Any] = {
        "coraRunId": cora_run_id,
        "userId": req.user_id,
        "status": status,
        "mode": mode,
        "modelId": model_id,
        "intake": req.model_dump(by_alias=True),
        "llmProvider": provider,
    }
    save_run(base_record)

    try:
        skill_id = normalize_skill_id(req.skill_id)
        images = await _resolve_images(req)
        seed_text = _seed_from_attachments(req)
        force_cover = bool(images) or bool((req.cover or "").strip())

        design = decide_design(
            cora_run_id=cora_run_id,
            topic=req.topic,
            slides_count=slides_count,
            skill_id=skill_id,
            force_cover=force_cover,
        )

        plan = build_skeleton_plan(
            cora_run_id=cora_run_id,
            mode=mode,
            topic=req.topic,
            language=req.language,
            ratio=req.ratio,
            slides_count=slides_count,
            model_id=model_id,
            brand=_brand_dict(req),
            seed_text=seed_text or None,
            design=design,
        )
        if skill_id:
            plan.setdefault("analysis", {})
            if isinstance(plan["analysis"], dict):
                plan["analysis"]["intent"] = skill_id
                plan["analysis"]["skillId"] = skill_id
        save_run({**base_record, "status": "planning", "plan": plan})

        status = "executing"
        save_run({**base_record, "status": status, "plan": plan})

        design = plan.get("design") or {}
        has_cover = bool(design.get("hasCover", True))
        use_aesthetic = str(design.get("engine") or "") == "aesthetic_llm" or skill_id == "aesthetic"

        font_override = resolve_font(req.font)
        if not font_override and req.brand_kit and req.brand_kit.fonts:
            for candidate in req.brand_kit.fonts:
                font_override = resolve_font(candidate)
                if font_override:
                    break

        if use_aesthetic:
            from app.cora.aesthetic import (
                assemble_aesthetic_carousel,
                fill_aesthetic_photo_sets,
                generate_aesthetic_carousel,
                seed_photo_sets_from_user,
                to_slide_contents,
            )

            aesthetic = await generate_aesthetic_carousel(
                topic=req.topic,
                slides_count=slides_count,
                language=req.language,
                handle=req.handle,
                model_id=model_id,
                seed_text=seed_text,
            )
            slides = to_slide_contents(aesthetic)
            photo_sets = seed_photo_sets_from_user(
                slides=aesthetic["slides"],
                user_images=images,
            )
            orientation = {
                "1:1": "square",
                "16:9": "landscape",
            }.get(req.ratio, "portrait")
            photo_sets = await fill_aesthetic_photo_sets(
                slides=aesthetic["slides"],
                photo_sets=photo_sets,
                topic=req.topic,
                salt=cora_run_id,
                orientation=orientation,
                use_stock=bool(req.stock_photos),
            )
            cover_src = ""
            if photo_sets and photo_sets[0]:
                cover_src = photo_sets[0][0] if photo_sets[0] else ""

            mood = str(aesthetic.get("moodHint") or design.get("mood") or "pinterest_editorial")
            palette = await generate_palette(
                topic=req.topic,
                language=req.language,
                model_id=model_id,
                mood=mood,
            )
            typography = await generate_typography(
                topic=req.topic,
                language=req.language,
                mood=mood,
                model_id=model_id,
                show_handle=bool(req.show_handle),
                font_override=font_override,
            )
            if isinstance(design, dict):
                design["typography"] = typography.to_dict()
                design["fontFamily"] = typography.font_family
                design["showHandle"] = typography.show_handle
                design["engine"] = "aesthetic_llm"
                design["mood"] = mood
                design["aesthetic"] = {
                    "moodHint": aesthetic.get("moodHint"),
                    "slideCount": len(aesthetic.get("slides") or []),
                }
                plan["design"] = design
            plan["aesthetic"] = aesthetic

            status = "assembling"
            plan = bind_content_to_plan(plan, slides)
            assembled = assemble_aesthetic_carousel(
                aesthetic=aesthetic,
                ratio=req.ratio,
                palette=palette,
                plan=plan,
                cora_run_id=cora_run_id,
                save=req.save,
                slide_photo_sets=photo_sets,
                typography=typography,
                handle=req.handle if req.show_handle else (req.handle or ""),
                show_handle=bool(req.show_handle),
            )
        else:
            slide_photos = _assign_slide_photos(
                images=images,
                slides_count=slides_count,
                has_cover=has_cover,
            )
            cover_src = slide_photos[0] if has_cover and slide_photos else ""

            topic_for_llm = req.topic
            skill_brief = skill_prompt_brief(skill_id) or str(design.get("skillBrief") or "")
            if skill_brief:
                topic_for_llm = f"{skill_brief}\n\nBrief: {req.topic}"
            if seed_text:
                topic_for_llm = f"{topic_for_llm}\n\nSource copy:\n{seed_text}"

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
                plan=plan,
            )

            use_stock = bool(req.stock_photos) and stock_photos_enabled()
            if use_stock:
                orientation = {
                    "1:1": "square",
                    "16:9": "landscape",
                }.get(req.ratio, "portrait")
                slide_photos = await fill_slide_photos_from_prompts(
                    slides=slides,
                    slide_photos=slide_photos,
                    topic=req.topic,
                    salt=cora_run_id,
                    has_cover=has_cover,
                    orientation=orientation,
                )
                # Скачать URL стока → data URL (как user cover), чтобы Fabric не упирался в CORS
                resolved_photos: list[str] = []
                for src in slide_photos:
                    if not (src or "").strip():
                        resolved_photos.append("")
                        continue
                    try:
                        resolved_photos.append(await resolve_cover_src(src))
                    except Exception:
                        resolved_photos.append("")
                slide_photos = resolved_photos
                cover_src = slide_photos[0] if has_cover and slide_photos else cover_src

            content = content_from_raw(
                raw=raw,
                slides=slides,
                handle=req.handle if req.show_handle else (req.handle or ""),
                cover_src=cover_src,
            )
            mood = str(design.get("mood") or "")
            palette = await generate_palette(
                topic=req.topic,
                language=req.language,
                model_id=model_id,
                mood=mood,
            )
            typography = await generate_typography(
                topic=req.topic,
                language=req.language,
                mood=mood,
                model_id=model_id,
                show_handle=bool(req.show_handle),
                font_override=font_override,
            )
            if isinstance(design, dict):
                design["typography"] = typography.to_dict()
                design["fontFamily"] = typography.font_family
                design["showHandle"] = typography.show_handle
                plan["design"] = design

            status = "assembling"
            plan = bind_content_to_plan(plan, slides)
            assembled = assemble_carousel(
                content=content,
                ratio=req.ratio,
                palette=palette,
                plan=plan,
                cora_run_id=cora_run_id,
                save=req.save,
                slide_photos=slide_photos,
                typography=typography,
            )
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
            llmProvider=provider,
        )
        save_run(
            {
                **base_record,
                **response.model_dump(),
                "status": "done",
            }
        )
        return response
    except Exception as exc:
        err = f"CORA failed ({status}): {exc}"
        save_run(
            {
                **base_record,
                "status": "failed",
                "error": err,
            }
        )
        raise RuntimeError(err) from exc
