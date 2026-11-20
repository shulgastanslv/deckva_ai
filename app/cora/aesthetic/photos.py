"""Multi-slot stock photos for aesthetic portrait / collage variants."""

from __future__ import annotations

from typing import Any

from app.cover_media import resolve_cover_src
from app.schemas import SlideContent
from app.stock_photos import search_stock_photo, stock_photos_enabled
from app.templates.aesthetic import aesthetic_variant_for, photo_slot_count, pick_cover_variant

_EXTRA_FLAVORS = (
    "editorial lifestyle detail flat lay",
    "cozy aesthetic still life warm light",
    "autumn flowers bouquet hands",
    "coffee mug top down lifestyle",
    "knit sweater book leaves aesthetic",
)


def _prompts_for_slide(
    slide: SlideContent,
    *,
    slots: int,
    topic: str,
    variant: str,
) -> list[str]:
    primary = (slide.image_prompt or "").strip() or f"editorial lifestyle aesthetic {topic}"
    out = [primary]
    extras: list[str] = []
    if variant == "collage":
        for it in slide.items or []:
            text = str(it).strip()
            if not text:
                continue
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(1, len(text))
            words = text.split()
            if ascii_ratio > 0.85 and 3 <= len(words) <= 12:
                extras.append(text)
    fi = 0
    while len(out) + len(extras) < slots:
        flavor = _EXTRA_FLAVORS[fi % len(_EXTRA_FLAVORS)]
        extras.append(f"{flavor} {topic}".strip())
        fi += 1
    out.extend(extras)
    return out[:slots]


async def _resolve_row(row: list[str]) -> list[str]:
    out: list[str] = []
    for src in row:
        if not (src or "").strip():
            out.append("")
            continue
        try:
            out.append(await resolve_cover_src(src))
        except Exception:
            out.append("")
    return out


async def build_aesthetic_photo_sets(
    *,
    slides: list[SlideContent],
    slide_photos: list[str],
    topic: str,
    salt: str,
    seed: int | str | None = None,
    design: dict[str, Any] | None = None,
    orientation: str = "portrait",
    use_stock: bool = True,
) -> list[list[str]]:
    """One photo list per slide, sized to the fixed template variant."""
    design = dict(design or {})
    if not str(design.get("aestheticCoverVariant") or "").strip():
        design["aestheticCoverVariant"] = pick_cover_variant(
            seed if seed is not None else salt
        )

    n = len(slides)
    sets: list[list[str]] = []
    used: set[str] = set()
    stock_on = use_stock and stock_photos_enabled()

    for i, slide in enumerate(slides):
        variant = aesthetic_variant_for(index=i, total=n, design=design)
        slots = photo_slot_count(variant)
        row = [""] * slots
        primary = slide_photos[i] if i < len(slide_photos) else ""
        if (primary or "").strip():
            row[0] = primary.strip()

        prompts = _prompts_for_slide(slide, slots=slots, topic=topic, variant=variant)
        if stock_on:
            for slot in range(slots):
                if (row[slot] or "").strip():
                    continue
                q = prompts[slot] if slot < len(prompts) else prompts[0]
                url = await search_stock_photo(
                    q,
                    salt=salt,
                    slide_index=i * 10 + slot,
                    orientation=orientation,
                    used_ids=used,
                )
                if url:
                    row[slot] = url
        sets.append(row)

    return [await _resolve_row(row) for row in sets]
