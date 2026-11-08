"""ASSEMBLE: content + palette → Fabric carousel, stamp coraObjectId."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from app.palette import Palette
from app.schemas import CarouselContent, PaletteResponse, SlideContent
from app.template import build_carousel

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    if not text:
        raise RuntimeError("Не удалось сформировать имя файла из title.")
    return text[:48]


def palette_response(p: Palette) -> PaletteResponse:
    return PaletteResponse(**p.to_dict())


def stamp_cora_object_ids(carousel: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Привязать text/image слои canvas к object.id из CarouselPlan."""
    slides = carousel.get("slides") or []
    for slide_meta in plan.get("slides", []):
        idx = int(slide_meta.get("index", -1))
        if idx < 0 or idx >= len(slides):
            continue
        fabric = slides[idx]
        objects = fabric.get("objects") or []
        plan_objs = slide_meta.get("objects") or []

        headline_id = next((o["id"] for o in plan_objs if o.get("role") == "headline"), None)
        body_id = next(
            (o["id"] for o in plan_objs if o.get("role") in {"body", "sub", "cta"}),
            None,
        )
        cover_id = next((o["id"] for o in plan_objs if o.get("role") == "cover"), None)

        headed = False
        bodied = False
        for obj in objects:
            typ = obj.get("type")
            style = obj.get("swibpStyle")
            role = obj.get("swibpRole")
            if typ == "Textbox" and style == "heading" and headline_id and not headed:
                obj["coraObjectId"] = headline_id
                headed = True
            elif (
                typ == "Textbox"
                and style == "body"
                and role not in {"handle", "counter"}
                and body_id
                and not bodied
            ):
                obj["coraObjectId"] = body_id
                bodied = True
            elif typ == "Image" and cover_id and "coraObjectId" not in obj:
                obj["coraObjectId"] = cover_id
    return carousel


def assemble_carousel(
    *,
    content: CarouselContent,
    ratio: str,
    palette: Palette,
    plan: dict[str, Any],
    cora_run_id: str,
    save: bool,
) -> dict[str, Any]:
    seed = int(time.time() * 1000) % 2_147_483_647
    carousel = build_carousel(content, aspect_ratio=ratio, palette=palette, seed=seed)
    carousel = stamp_cora_object_ids(carousel, plan)

    path: str | None = None
    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / f"{int(time.time())}_{slug(content.title)}.json"
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

    return {
        "title": content.title,
        "aspectRatio": carousel["aspectRatio"],
        "width": carousel["width"],
        "height": carousel["height"],
        "path": path,
        "palette": palette_response(palette),
        "carousel": {
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "slides": carousel["slides"],
        },
    }


def content_from_raw(
    *,
    raw: dict[str, Any],
    slides: list[SlideContent],
    handle: str,
    cover_src: str,
) -> CarouselContent:
    from app.content import require_category, require_str

    return CarouselContent(
        title=require_str(raw.get("title"), "title"),
        tagline=str(raw.get("tagline", "")).strip(),
        handle=handle,
        category=require_category(raw.get("category")),
        cover=cover_src,
        slides=slides,
    )
