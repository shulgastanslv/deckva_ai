"""Aesthetic skill — one skill, randomized cover families from references.

Cover pool (server RNG):
1. portrait  — full-bleed, centered title + /cue/
2. editorial — full-bleed, left cream hook with [brackets], footer corners
3. diptych   — vertical 50/50 photos, centered title + /сохраняй/
4. collage   — equal 2×2 + centered black title bar
5. manifesto — full-bleed, huge stacked centered slogan
6. niches    — full-bleed + floating niche tags + bracket title

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
    split_stack,
    text_h,
    textbox,
)
from app.templates.default import DefaultTemplate

CREAM = "#F2E6A8"
CREAM_SOFT = "#EDE4D0"
WHITE = "#FFFFFF"
BLACK = "#111111"

COVER_VARIANTS = ("portrait", "editorial", "diptych", "collage", "manifesto", "niches")
MID_VARIANTS = ("portrait", "diptych", "collage", "editorial")
CTA_VARIANT = "cta_soft"

PHOTO_SLOTS: dict[str, int] = {
    "portrait": 1,
    "editorial": 1,
    "diptych": 2,
    "collage": 4,
    "manifesto": 1,
    "niches": 1,
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


def _bracket_highlight(text: str) -> str:
    """Wrap the last word in [brackets] like the editorial references."""
    raw = clip(text, 90).strip()
    if not raw:
        return raw
    if "[" in raw and "]" in raw:
        return raw.lower()
    parts = raw.split()
    if len(parts) < 2:
        return raw.lower()
    parts[-1] = f"[{parts[-1].strip('[],')}]"
    return " ".join(parts).lower()


def _save_cue(s: SlideContent, fallback: str = "сохраняй") -> str:
    call = clip(s.callout or s.body or fallback, 36).lower().strip().strip("/")
    return f"/{call or fallback}/"


def pick_cover_variant(key: str | int | None = None) -> str:
    """Stable cover pick from run id / seed (no shared RNG drift)."""
    if key is None or key == "":
        return COVER_VARIANTS[0]
    if isinstance(key, int):
        return COVER_VARIANTS[key % len(COVER_VARIANTS)]
    name = str(key).strip()
    if name in COVER_VARIANTS:
        return name
    # Legacy aliases from old separate skills
    legacy = {"lookbook": "diptych", "lifestyle": "editorial"}
    if name in legacy:
        return legacy[name]
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
    mid = list(MID_VARIANTS)
    if rng is not None:
        return mid[rng.randrange(len(mid))]
    return mid[(index - 1) % len(mid)]


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
    """One aesthetic skill — cover family randomized per run."""

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
            "editorial": self._lay_editorial,
            "diptych": self._lay_diptych,
            "collage": self._lay_collage,
            "manifesto": self._lay_manifesto,
            "niches": self._lay_niches,
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

    # —— Variant: editorial (ref — left cream hook + footer) ——

    def _lay_editorial(
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
        """Full-bleed + left cream headline with [brackets] + footer corners."""
        objs = _photo_or_placeholder(lay, photos[0] if photos else "", palette, dim=0.16, slot=0)
        pad = lay.pad
        is_cover = index == 0

        if is_cover:
            heading = _bracket_highlight(s.heading or category)
            body = clip(s.body or s.callout or "", 48).lower()
            head_size = max(self.head_px + 4, 44)
            title_w = lay.w * 0.72
            th = text_h(heading, head_size, title_w)
            title_top = lay.h * 0.38
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
                    text_align="left",
                    line_height=1.02,
                    swibp_style="heading",
                )
            )
            if body:
                objs.append(
                    textbox(
                        body,
                        left=pad,
                        top=title_top + th + 14,
                        width=title_w * 0.85,
                        font_size=scaled_size(SIZE_META, kind="meta") + 4,
                        font_family=current_font(),
                        fill=CREAM,
                        font_weight="500",
                        text_align="left",
                        swibp_style="body",
                    )
                )
        else:
            objs.extend(_corner_top(lay, left_lines=_meta_lines(category, ""), handle=handle, fill=WHITE))
            caption = _meta_lines(clip(s.heading, 60), clip(s.body or "", 60))
            objs.extend(
                _caption_block(
                    lay,
                    caption,
                    fill=WHITE,
                    font_size=max(22, self.head_px - 14),
                )
            )

        objs.extend(
            _corner_footer(
                lay,
                tag=s.tag or "блог про интеллектуальный блогинг & посты-карусели",
                handle=handle,
                fill=WHITE,
            )
        )
        return slide(BLACK, objs, width=lay.w, height=lay.h)

    # —— Variant: diptych (ref — vertical split lookbook) ——

    def _lay_diptych(
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
        """Top/bottom half photos + centered title + /save/ cue."""
        half = lay.h / 2
        top_src = photos[0] if photos else ""
        bot_src = photos[1] if len(photos) > 1 else (photos[0] if photos else "")
        objs: list[dict[str, Any]] = []
        objs.extend(
            _photo_cell(top_src, left=0, top=0, width=float(lay.w), height=half, palette=palette, dim=0.12, slot=0)
        )
        objs.extend(
            _photo_cell(
                bot_src, left=0, top=half, width=float(lay.w), height=half, palette=palette, dim=0.12, slot=1
            )
        )

        tagline = _meta_lines(
            s.tag or category or "эстетика в маленьком городе",
            (s.badges[0] if s.badges else "") or "превращаю обычное в особенное",
        )
        objs.extend(_corner_top(lay, left_lines=tagline, handle=handle, fill=WHITE))

        heading = clip(s.heading, 90).lower()
        head_size = max(self.head_px, 40)
        title_w = lay.w - lay.pad * 2
        th = text_h(heading, head_size, title_w)
        title_top = (lay.h - th) / 2 - head_size * 0.2
        objs.append(
            textbox(
                heading,
                left=lay.pad,
                top=title_top,
                width=title_w,
                font_size=head_size,
                font_family=current_font(),
                fill=WHITE,
                font_weight="700",
                text_align="center",
                line_height=1.02,
                swibp_style="heading",
            )
        )
        objs.append(
            textbox(
                _save_cue(s),
                left=lay.pad,
                top=title_top + th + 14,
                width=title_w,
                font_size=scaled_size(SIZE_META, kind="meta") + 2,
                font_family=current_font(),
                fill=WHITE,
                font_weight="400",
                text_align="center",
                swibp_style="body",
            )
        )
        return slide(BLACK, objs, width=lay.w, height=lay.h)

    # —— Variant: manifesto ——

    def _lay_manifesto(
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
        """Full-bleed + huge stacked centered statement."""
        objs = _photo_or_placeholder(lay, photos[0] if photos else "", palette, dim=0.2, slot=0)
        objs.extend(_corner_top(lay, left_lines=[], handle=handle, fill=WHITE))

        lines = split_stack(clip(s.heading, 80).upper(), max_lines=5)
        line_size = max(self.head_px + 16, 56)
        line_gap = 6
        block_h = len(lines) * (line_size * 0.95 + line_gap)
        y = (lay.h - block_h) / 2
        for line in lines:
            objs.append(
                textbox(
                    line,
                    left=lay.pad,
                    top=y,
                    width=lay.w - lay.pad * 2,
                    font_size=line_size,
                    font_family=current_font(),
                    fill=WHITE,
                    font_weight="700",
                    text_align="center",
                    line_height=0.92,
                    swibp_style="heading",
                )
            )
            y += line_size * 0.95 + line_gap

        note = clip(s.body or s.callout, 90)
        if note:
            objs.append(
                textbox(
                    f"* {note}",
                    left=lay.w * 0.35,
                    top=lay.h - lay.pad * 2.6,
                    width=lay.w * 0.55,
                    font_size=18,
                    font_family=current_font(),
                    fill=CREAM_SOFT,
                    font_weight="500",
                    swibp_style="body",
                )
            )
        objs.extend(footer(lay, category, fill_cat=WHITE, fill_arrow=CREAM))
        return slide(BLACK, objs, width=lay.w, height=lay.h)

    # —— Variant: niches ——

    def _lay_niches(
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
        """Full-bleed + bracket title + floating niche tags from items."""
        objs = _photo_or_placeholder(lay, photos[0] if photos else "", palette, dim=0.12, slot=0)
        title = clip(s.heading, 48)
        objs.append(
            textbox(
                f"[ {title.lower()} ]",
                left=lay.pad,
                top=lay.pad * 1.1,
                width=lay.w - lay.pad * 2,
                font_size=28,
                font_family=current_font(),
                fill=CREAM,
                font_weight="700",
                text_align="center",
                swibp_style="heading",
            )
        )
        if s.body:
            objs.append(
                textbox(
                    clip(s.body, 40).lower(),
                    left=lay.pad,
                    top=lay.pad * 1.1 + 40,
                    width=lay.w * 0.4,
                    font_size=22,
                    font_family=current_font(),
                    fill=CREAM,
                    font_weight="600",
                    swibp_style="body",
                )
            )

        tags = [clip(t, 22).lower() for t in (s.items or [])[:8] if str(t).strip()]
        if not tags and s.badges:
            tags = [clip(t, 22).lower() for t in s.badges[:6] if str(t).strip()]
        left_x = lay.pad * 0.85
        right_x = lay.w * 0.58
        y_left = lay.h * 0.28
        y_right = lay.h * 0.32
        for i, tag in enumerate(tags):
            on_left = i % 2 == 0
            objs.append(
                textbox(
                    tag,
                    left=left_x if on_left else right_x,
                    top=y_left if on_left else y_right,
                    width=lay.w * 0.36,
                    font_size=26,
                    font_family=current_font(),
                    fill=CREAM,
                    font_weight="700",
                    swibp_style="body",
                )
            )
            if on_left:
                y_left += 52
            else:
                y_right += 56

        objs.extend(
            _corner_footer(
                lay,
                tag=clip(s.callout or s.tag or category, 48),
                handle=handle,
                fill=WHITE,
            )
        )
        return slide(BLACK, objs, width=lay.w, height=lay.h)

    # —— Variant: collage ——

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
    def layout_cover(
        self,
        s,
        lay,
        handle,
        category,
        palette,
        *,
        index,
        with_grid,
        cover_src,
        photo_ratio=1.0,
        cover_placement="top",
        cover_rounded=False,
    ):
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
