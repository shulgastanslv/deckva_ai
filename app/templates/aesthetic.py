"""Aesthetic skill templates — two even Pinterest layouts from references.

1. portrait — full-bleed photo, axis-aligned corner meta + caption
2. collage  — equal 2×2 grid, centered black title bar, footer corners

LLM only fills SlideContent. Geometry lives here.
"""

from __future__ import annotations

import random
from typing import Any, ClassVar

from app.fonts import Typography, current_font, scaled_size
from app.palette import Palette
from app.schemas import CarouselContent, SlideContent
from app.templates.base import (
    GAP,
    SIZE_META,
    L,
    clip,
    footer,
    full_bleed_photo,
    image,
    rect,
    slide,
    text_h,
    textbox,
)
from app.templates.default import DefaultTemplate

CREAM = "#F2E6A8"
CREAM_SOFT = "#EDE4D0"
WHITE = "#FFFFFF"
BLACK = "#111111"

# Exactly two even families (+ soft CTA).
COVER_VARIANTS = ("portrait", "collage")
MID_VARIANTS = ("portrait", "collage")
CTA_VARIANT = "cta_soft"

PHOTO_SLOTS: dict[str, int] = {
    "portrait": 1,
    "collage": 4,
    "cta_soft": 1,
}

# Яркие плейсхолдеры слотов «здесь будет фото» (пока нет картинки).
PHOTO_PLACEHOLDERS: tuple[str, ...] = (
    "#FF2D55",  # pink
    "#00C7BE",  # teal
    "#FFD60A",  # yellow
    "#5E5CE6",  # indigo
)


def _placeholder_fill(slot: int = 0) -> str:
    return PHOTO_PLACEHOLDERS[slot % len(PHOTO_PLACEHOLDERS)]


def _photo_or_placeholder(
    lay: L,
    src: str,
    palette: Palette,
    *,
    dim: float = 0.18,
    slot: int = 0,
) -> list[dict[str, Any]]:
    """Full-bleed photo, or a bright rect so empty slots are obvious."""
    if (src or "").strip():
        return full_bleed_photo(lay, src, palette, dim=dim)
    return [
        rect(
            left=0,
            top=0,
            width=lay.w,
            height=lay.h,
            fill=_placeholder_fill(slot),
            swibp_slot="image",
        )
    ]


def _photo_cell(
    src: str,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    palette: Palette,
    dim: float = 0.12,
    slot: int = 0,
) -> list[dict[str, Any]]:
    if (src or "").strip():
        objs: list[dict[str, Any]] = [
            image(src.strip(), left=left, top=top, width=width, height=height, swibp_slot="image")
        ]
        if dim > 0:
            objs.append(
                rect(
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    fill="#000000",
                    opacity=dim,
                    swibp_slot="accent",
                )
            )
        return objs
    # Empty slot: bright solid, no dim — easy to spot missing photos.
    return [
        rect(
            left=left,
            top=top,
            width=width,
            height=height,
            fill=_placeholder_fill(slot),
            swibp_slot="image",
        )
    ]


def _meta_lines(primary: str, secondary: str) -> list[str]:
    """Two short lowercase lines for top-left / bottom-left blocks."""
    a = clip(primary, 42).lower().strip()
    b = clip(secondary, 42).lower().strip()
    lines = [x for x in (a, b) if x]
    return lines[:2] or [""]


def pick_cover_variant(key: str | int | None = None) -> str:
    """Stable cover pick from run id / seed (no shared RNG drift)."""
    if key is None or key == "":
        return COVER_VARIANTS[0]
    if isinstance(key, int):
        return COVER_VARIANTS[key % len(COVER_VARIANTS)]
    name = str(key).strip()
    if name in COVER_VARIANTS:
        return name
    return COVER_VARIANTS[sum(ord(c) for c in str(key)) % len(COVER_VARIANTS)]


def aesthetic_variant_for(
    *,
    index: int,
    total: int,
    rng: random.Random | None = None,
    design: dict[str, Any] | None = None,
) -> str:
    design = design or {}
    if index == 0:
        forced = str(design.get("aestheticCoverVariant") or "").strip()
        if forced in COVER_VARIANTS:
            return forced
        if rng is not None:
            return COVER_VARIANTS[rng.randrange(len(COVER_VARIANTS))]
        return COVER_VARIANTS[0]
    if index == total - 1:
        return CTA_VARIANT
    return MID_VARIANTS[(index - 1) % len(MID_VARIANTS)]


def photo_slot_count(variant: str) -> int:
    return PHOTO_SLOTS.get(str(variant or "").strip(), 1)


def _corner_top(
    lay: L,
    *,
    left_lines: list[str],
    handle: str,
    fill: str = WHITE,
) -> list[dict[str, Any]]:
    """Ref: top-left 1–2 lines + top-right @handle, same pad on both sides."""
    meta = scaled_size(SIZE_META, kind="meta")
    pad = lay.pad
    objs: list[dict[str, Any]] = []
    y = pad
    for line in left_lines[:2]:
        if not line:
            continue
        objs.append(
            textbox(
                line,
                left=pad,
                top=y,
                width=lay.w * 0.58,
                font_size=meta,
                font_family=current_font(),
                fill=fill,
                font_weight="500",
                text_align="left",
                line_height=1.15,
                swibp_style="body",
            )
        )
        y += meta * 1.25
    if handle:
        objs.append(
            textbox(
                handle,
                left=lay.w * 0.55,
                top=pad,
                width=lay.w * 0.45 - pad,
                font_size=meta,
                font_family=current_font(),
                fill=fill,
                font_weight="500",
                text_align="right",
                swibp_style="body",
                swibp_role="handle",
            )
        )
    return objs


def _corner_footer(
    lay: L,
    *,
    tag: str,
    handle: str,
    fill: str = WHITE,
) -> list[dict[str, Any]]:
    """Ref: bottom-left blog line + bottom-right @handle, shared baseline."""
    meta = scaled_size(SIZE_META, kind="meta")
    pad = lay.pad
    top = lay.h - pad - meta
    objs: list[dict[str, Any]] = []
    if tag:
        objs.append(
            textbox(
                clip(tag, 48).lower(),
                left=pad,
                top=top,
                width=lay.w * 0.55,
                font_size=meta,
                font_family=current_font(),
                fill=fill,
                font_weight="500",
                opacity=0.92,
                swibp_style="body",
            )
        )
    if handle:
        objs.append(
            textbox(
                handle,
                left=lay.w * 0.55,
                top=top,
                width=lay.w * 0.45 - pad,
                font_size=meta,
                font_family=current_font(),
                fill=fill,
                font_weight="500",
                text_align="right",
                opacity=0.92,
                swibp_style="body",
                swibp_role="handle",
            )
        )
    return objs


def _caption_block(
    lay: L,
    lines: list[str],
    *,
    fill: str = WHITE,
    font_size: int | None = None,
) -> list[dict[str, Any]]:
    """Ref: bottom-left shot labels — left-aligned, shared left edge with top meta."""
    size = font_size or max(22, scaled_size(SIZE_META, kind="meta") + 4)
    pad = lay.pad
    # Sit above the footer band
    block_h = len([ln for ln in lines if ln]) * size * 1.2
    y = lay.h - pad * 2.4 - block_h
    objs: list[dict[str, Any]] = []
    for line in lines:
        if not line:
            continue
        objs.append(
            textbox(
                line.lower(),
                left=pad,
                top=y,
                width=lay.w * 0.62,
                font_size=size,
                font_family=current_font(),
                fill=fill,
                font_weight="500",
                text_align="left",
                line_height=1.15,
                swibp_style="heading",
            )
        )
        y += size * 1.2
    return objs


def _center_title_bar(
    lay: L,
    text: str,
    *,
    fill_bg: str = BLACK,
    fill_text: str = WHITE,
) -> list[dict[str, Any]]:
    """Ref: black rounded bar centered on the 2×2 cross."""
    label = clip(text, 72).lower().strip() or " "
    size = max(20, min(28, scaled_size(SIZE_META, kind="meta") + 6))
    max_w = lay.w * 0.78
    # Approx width from character count; clamp to readable band.
    approx = max(160.0, min(max_w, len(label) * size * 0.52 + 56))
    th = text_h(label, size, approx - 48)
    bar_h = max(44.0, th + 28)
    left = (lay.w - approx) / 2
    top = (lay.h - bar_h) / 2
    rx = min(18.0, bar_h / 2)
    return [
        rect(
            left=left,
            top=top,
            width=approx,
            height=bar_h,
            fill=fill_bg,
            rx=rx,
            ry=rx,
            opacity=0.92,
            swibp_slot="accent",
        ),
        textbox(
            label,
            left=left + 24,
            top=top + (bar_h - th) / 2 - 2,
            width=approx - 48,
            font_size=size,
            font_family=current_font(),
            fill=fill_text,
            font_weight="600",
            text_align="center",
            line_height=1.1,
            swibp_style="heading",
        ),
    ]


class AestheticTemplate(DefaultTemplate):
    """Pinterest aesthetic: two even layout variants, normal content pipeline."""

    skill_id: ClassVar[str | None] = "aesthetic"
    head_size: ClassVar[int] = 42

    def design_defaults(self) -> dict[str, Any]:
        return {
            **super().design_defaults(),
            "photoRatio": 1.0,
            "gridMode": "none",
            "accentBias": 0.2,
            "hasCover": True,
            "mood": "pinterest_editorial",
        }

    def build_slide(
        self,
        s: SlideContent,
        *,
        index: int,
        total: int,
        lay: L,
        handle: str,
        category: str,
        cover_src: str,
        palette: Palette,
        rng: random.Random,
        design: dict[str, Any] | None = None,
        slide_photo: str = "",
    ) -> dict[str, Any]:
        design = self.merge_design(design)
        variant = aesthetic_variant_for(index=index, total=total, rng=rng, design=design)
        sets = design.get("slidePhotoSets") or []
        photos: list[str] = []
        if isinstance(sets, list) and index < len(sets) and isinstance(sets[index], list):
            photos = [str(p or "") for p in sets[index]]
        primary = (slide_photo or "").strip() or ((cover_src or "").strip() if index == 0 else "")
        if not photos:
            photos = [primary] if primary else [""]
        elif primary and not (photos[0] or "").strip():
            photos[0] = primary

        builders = {
            "portrait": self._lay_portrait,
            "collage": self._lay_collage,
            "cta_soft": self._lay_cta_soft,
        }
        builder = builders.get(variant, self._lay_portrait)
        return builder(
            s,
            lay,
            handle,
            category,
            palette,
            index=index,
            total=total,
            photos=photos,
            variant=variant,
        )

    def build_carousel(
        self,
        content: CarouselContent,
        *,
        aspect_ratio: str,
        palette: Palette,
        seed: int | None = None,
        design: dict[str, Any] | None = None,
        slide_photos: list[str] | None = None,
        typography: Typography | None = None,
    ) -> dict[str, Any]:
        out = super().build_carousel(
            content,
            aspect_ratio=aspect_ratio,
            palette=palette,
            seed=seed,
            design=design,
            slide_photos=slide_photos,
            typography=typography,
        )
        out["templateId"] = "aesthetic"
        if isinstance(out.get("design"), dict):
            out["design"]["templateId"] = "aesthetic"
            out["design"].pop("engine", None)
        return out

    # —— Variant 1: portrait ——

    def _lay_portrait(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
        total: int,
        photos: list[str],
        variant: str,
    ) -> dict[str, Any]:
        """Full-bleed + even corners. Cover: centered straight title; mid: left caption."""
        objs = _photo_or_placeholder(lay, photos[0] if photos else "", palette, dim=0.18, slot=0)
        pad = lay.pad

        tagline = _meta_lines(
            s.tag or category or "эстетика",
            (s.badges[0] if s.badges else "") or "превращаю обычное в особенное",
        )
        objs.extend(_corner_top(lay, left_lines=tagline, handle=handle, fill=WHITE))

        is_cover = index == 0
        heading = clip(s.heading, 90).lower()
        body = clip(s.body or s.callout or "", 80).lower()

        if is_cover:
            # Straight centered title (no wave / zigzag).
            head_size = max(self.head_px, 40)
            title_w = lay.w - pad * 2
            th = text_h(heading, head_size, title_w)
            title_top = (lay.h - th) / 2 - head_size * 0.15
            objs.append(
                textbox(
                    heading,
                    left=pad,
                    top=title_top,
                    width=title_w,
                    font_size=head_size,
                    font_family=current_font(),
                    fill=CREAM,
                    font_weight="700",
                    text_align="center",
                    line_height=1.05,
                    swibp_style="heading",
                )
            )
            call = clip(s.callout or body, 36).lower()
            if call:
                if not (call.startswith("/") and call.endswith("/")):
                    call = f"/{call.strip('/')}/"
                objs.append(
                    textbox(
                        call,
                        left=pad,
                        top=title_top + th + 16,
                        width=title_w,
                        font_size=scaled_size(SIZE_META, kind="meta") + 2,
                        font_family=current_font(),
                        fill=WHITE,
                        font_weight="400",
                        text_align="center",
                        swibp_style="body",
                    )
                )
        else:
            # Mid: left caption block — heading + body as two even lines.
            caption = _meta_lines(heading, body or (s.tag or ""))
            if not caption[0]:
                caption = _meta_lines(category, "кадр")
            objs.extend(
                _caption_block(
                    lay,
                    caption,
                    fill=WHITE,
                    font_size=max(22, self.head_px - 14),
                )
            )

        return slide(BLACK, objs, width=lay.w, height=lay.h)

    # —— Variant 2: collage ——

    def _lay_collage(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
        total: int,
        photos: list[str],
        variant: str,
    ) -> dict[str, Any]:
        """Equal 2×2 cells + centered black title bar + even footer corners."""
        cell_w = lay.w / 2
        cell_h = lay.h / 2
        slots = [(0.0, 0.0), (cell_w, 0.0), (0.0, cell_h), (cell_w, cell_h)]
        objs: list[dict[str, Any]] = []
        for i, (x, y) in enumerate(slots):
            src = photos[i] if i < len(photos) else ""
            objs.extend(
                _photo_cell(
                    src,
                    left=x,
                    top=y,
                    width=cell_w,
                    height=cell_h,
                    palette=palette,
                    dim=0.14,
                    slot=i,
                )
            )

        objs.extend(_center_title_bar(lay, s.heading or category or "aesthetic"))
        objs.extend(
            _corner_footer(
                lay,
                tag=s.tag or "блог про интеллектуальный блогинг & посты-карусели",
                handle=handle,
                fill=WHITE,
            )
        )
        return slide(BLACK, objs, width=lay.w, height=lay.h)

    # —— CTA ——

    def _lay_cta_soft(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
        total: int,
        photos: list[str],
        variant: str,
    ) -> dict[str, Any]:
        src = photos[0] if photos else ""
        if src.strip():
            objs = full_bleed_photo(lay, src, palette, dim=0.28)
            bg = BLACK
        else:
            objs = _photo_or_placeholder(lay, "", palette, dim=0, slot=0)
            bg = _placeholder_fill(0)

        pad = lay.pad
        if handle:
            objs.extend(_corner_top(lay, left_lines=[], handle=handle, fill=WHITE))

        heading = clip(s.callout or s.heading, 100).lower()
        body = clip(s.body, 120) if s.body else ""
        head_size = max(32, self.head_px - 4)
        title_w = lay.w - pad * 2
        th = text_h(heading, head_size, title_w)
        y = (lay.h - th) / 2 - (28 if body else 0)
        objs.append(
            textbox(
                heading,
                left=pad,
                top=y,
                width=title_w,
                font_size=head_size,
                font_family=current_font(),
                fill=CREAM,
                font_weight="700",
                text_align="center",
                swibp_style="heading",
            )
        )
        if body:
            objs.append(
                textbox(
                    body,
                    left=lay.w * 0.12,
                    top=y + th + GAP,
                    width=lay.w * 0.76,
                    font_size=22,
                    font_family=current_font(),
                    fill=WHITE,
                    font_weight="500",
                    text_align="center",
                    swibp_style="body",
                )
            )
        objs.extend(footer(lay, category, fill_cat=CREAM_SOFT, fill_arrow=CREAM))
        return slide(bg, objs, width=lay.w, height=lay.h)

    # Unused abstract paths kept for DefaultTemplate compatibility
    def layout_cover(self, s, lay, handle, category, palette, *, index, with_grid, cover_src, photo_ratio=1.0):
        return self._lay_portrait(
            s, lay, handle, category, palette, index=index, total=index + 1, photos=[cover_src], variant="portrait"
        )

    def layout_content(self, s, lay, handle, category, palette, *, index, with_grid):
        return self._lay_portrait(
            s, lay, handle, category, palette, index=index, total=index + 1, photos=[""], variant="portrait"
        )

    def layout_accent_quote(self, s, lay, handle, category, palette, *, index):
        return self._lay_portrait(
            s, lay, handle, category, palette, index=index, total=index + 1, photos=[""], variant="portrait"
        )

    def layout_cta(self, s, lay, handle, category, palette, *, index, with_grid):
        return self._lay_cta_soft(
            s, lay, handle, category, palette, index=index, total=index + 1, photos=[""], variant="cta_soft"
        )
