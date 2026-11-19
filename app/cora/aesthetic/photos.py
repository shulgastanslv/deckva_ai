"""Multi-slot stock photos for aesthetic collage / split layouts."""

from __future__ import annotations

from typing import Any

from app.cover_media import resolve_cover_src
from app.stock_photos import search_stock_photo, stock_photos_enabled


def _empty_sets(slides: list[dict[str, Any]]) -> list[list[str]]:
    out: list[list[str]] = []
    for s in slides:
        n = max(1, len(s.get("image_prompts") or []))
        # photo slots may exceed prompts; size by max photo slot
        max_slot = 0
        for el in s.get("elements") or []:
            if el.get("kind") == "photo":
                max_slot = max(max_slot, int(el.get("slot") or 0))
        out.append([""] * (max(n, max_slot + 1)))
    return out


def seed_photo_sets_from_user(
    *,
    slides: list[dict[str, Any]],
    user_images: list[str],
) -> list[list[str]]:
    """Put user images into slide 0 slot0, then remaining mid-slide slots."""
    sets = _empty_sets(slides)
    if not user_images or not sets:
        return sets
    # cover first
    sets[0][0] = user_images[0]
    extras = user_images[1:]
    ei = 0
    for si in range(1, max(1, len(sets) - 1)):  # skip CTA
        for slot in range(len(sets[si])):
            if ei >= len(extras):
                return sets
            if not sets[si][slot]:
                sets[si][slot] = extras[ei]
                ei += 1
    return sets


async def fill_aesthetic_photo_sets(
    *,
    slides: list[dict[str, Any]],
    photo_sets: list[list[str]],
    topic: str,
    salt: str,
    orientation: str = "portrait",
    use_stock: bool = True,
) -> list[list[str]]:
    """Fill empty slots from image_prompts via Unsplash; resolve all to data URLs when possible."""
    n = len(slides)
    sets = [list(row) for row in photo_sets]
    while len(sets) < n:
        sets.append([])
    sets = sets[:n]

    used: set[str] = set()
    if use_stock and stock_photos_enabled():
        for i, s in enumerate(slides):
            prompts = list(s.get("image_prompts") or [])
            if i == n - 1 and not any((p or "").strip() for p in sets[i]):
                # CTA: optional single soft photo if prompt exists
                if not prompts:
                    continue
            row = sets[i]
            need = max(len(row), len(prompts), 1)
            while len(row) < need:
                row.append("")
            for slot, prompt in enumerate(prompts):
                if slot >= len(row):
                    row.append("")
                if row[slot].strip():
                    continue
                q = (prompt or "").strip() or f"editorial lifestyle aesthetic {topic}"
                url = await search_stock_photo(
                    q,
                    salt=salt,
                    slide_index=i * 10 + slot,
                    orientation=orientation,
                    used_ids=used,
                )
                if url:
                    row[slot] = url
            sets[i] = row

    # Resolve http(s) → data URL for Fabric safety
    resolved: list[list[str]] = []
    for row in sets:
        out_row: list[str] = []
        for src in row:
            if not (src or "").strip():
                out_row.append("")
                continue
            try:
                out_row.append(await resolve_cover_src(src))
            except Exception:
                out_row.append("")
        resolved.append(out_row)
    return resolved
