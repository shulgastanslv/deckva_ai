"""Оркестрация: cover → тексты → палитра → Fabric JSON."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from app.content import (
    generate_carousel_raw,
    generate_post_text,
    normalize_slides,
    require_category,
    require_str,
)
from app.cover_media import resolve_cover_src
from app.palette import Palette, generate_palette
from app.schemas import CarouselContent, GenerateRequest, PaletteResponse
from app.template import build_carousel

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    if not text:
        raise RuntimeError("Не удалось сформировать имя файла из title.")
    return text[:48]


def _palette_response(p: Palette) -> PaletteResponse:
    return PaletteResponse(**p.to_dict())


async def generate_carousel(req: GenerateRequest) -> dict[str, Any]:
    cover_src = await resolve_cover_src(req.cover)

    raw = await generate_carousel_raw(
        topic=req.topic,
        slides_count=req.slides_count,
        language=req.language,
        handle=req.handle,
    )
    slides = await normalize_slides(
        raw,
        topic=req.topic,
        slides_count=req.slides_count,
        language=req.language,
        handle=req.handle,
    )
    content = CarouselContent(
        title=require_str(raw.get("title"), "title"),
        tagline=str(raw.get("tagline", "")).strip(),
        handle=req.handle,
        category=require_category(raw.get("category")),
        cover=cover_src,
        slides=slides,
    )

    palette = await generate_palette(topic=req.topic, language=req.language)
    seed = int(time.time() * 1000) % 2_147_483_647
    carousel = build_carousel(content, aspect_ratio=req.aspect_ratio, palette=palette, seed=seed)

    path: str | None = None
    if req.save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / f"{int(time.time())}_{_slug(content.title)}.json"
        public = {
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "palette": palette.to_dict(),
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
        "palette": _palette_response(palette),
        "carousel": {
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "slides": carousel["slides"],
        },
    }


__all__ = ["generate_carousel", "generate_post_text", "generate_palette"]
