"""Shared layout helpers + abstract carousel template."""

from __future__ import annotations

import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from app.fabric import canvas_size, image, normalize_aspect, rect, slide, textbox
from app.palette import Palette
from app.schemas import CarouselContent, SlideContent

FONT = "Montserrat"
SIZE_HEAD = 55
SIZE_BODY = 25
SIZE_META = 20
GAP = 20
LINE_HEIGHT = 0.90
GRID_OPACITY = 0.22
PHOTO_TEXT_GAP = 2


@dataclass
class L:
    w: int
    h: int
    pad: float
    step: float


def make_layout(w: int, h: int) -> L:
    base = min(w, h)
    return L(w=w, h=h, pad=max(48, base * 0.06), step=max(72, base * 0.085))


def handle_text(h: str) -> str:
    h = h.strip()
    if not h:
        raise RuntimeError("Не указан handle.")
    return h if h.startswith("@") else f"@{h}"


def clip(t: str, n: int) -> str:
    t = (t or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def line_count(text: str, font_size: int, width: float) -> int:
    avg = font_size * 0.62
    total = 0
    for para in (text or " ").split("\n"):
        if not para.strip():
            total += 1
            continue
        words = para.split()
        cur = 0.0
        lines = 1
        for w in words:
            ww = len(w) * avg + avg * 0.4
            if cur + ww > width and cur > 0:
                lines += 1
                cur = ww
            else:
                cur += ww
        total += lines
    return max(1, total)


def text_h(text: str, font_size: int, width: float) -> float:
    lines = line_count(text, font_size, width)
    return lines * font_size * max(LINE_HEIGHT, 0.95) + 4


def grid(
    w: int,
    h: int,
    step: float,
    palette: Palette,
    *,
    top: float = 0,
    height: float | None = None,
) -> list[dict[str, Any]]:
    hh = height if height is not None else h - top
    objs: list[dict[str, Any]] = []
    x = 0.0
    while x <= w + 0.5:
        objs.append(
            rect(
                left=x,
                top=top,
                width=1.2,
                height=hh,
                fill=palette.grid,
                opacity=GRID_OPACITY,
                swibp_slot="accent",
            )
        )
        x += step
    y = top
    while y <= top + hh + 0.5:
        objs.append(
            rect(
                left=0,
                top=y,
                width=w,
                height=1.2,
                fill=palette.grid,
                opacity=GRID_OPACITY,
                swibp_slot="accent",
            )
        )
        y += step
    return objs


def counter(index: int, lay: L, *, fill: str) -> dict[str, Any]:
    return textbox(
        f"( {index + 1} )",
        left=lay.w - lay.pad - 140,
        top=lay.pad * 0.7,
        width=140,
        font_size=SIZE_META,
        font_family=FONT,
        fill=fill,
        font_weight="600",
        text_align="right",
        line_height=LINE_HEIGHT,
        swibp_style="body",
        swibp_role="counter",
    )


def footer(lay: L, category: str, *, fill_cat: str, fill_arrow: str) -> list[dict[str, Any]]:
    return [
        textbox(
            clip(category, 24),
            left=lay.pad,
            top=lay.h - lay.pad - SIZE_META,
            width=lay.w * 0.45,
            font_size=SIZE_META,
            font_family=FONT,
            fill=fill_cat,
            font_weight="500",
            text_align="left",
            line_height=LINE_HEIGHT,
            swibp_style="body",
        ),
        textbox(
            "→",
            left=lay.w - lay.pad - 48,
            top=lay.h - lay.pad - SIZE_META - 4,
            width=48,
            font_size=32,
            font_family=FONT,
            fill=fill_arrow,
            font_weight="bold",
            text_align="right",
            line_height=LINE_HEIGHT,
            swibp_style="body",
            swibp_slot="accent",
        ),
    ]


def text_block(
    text: str,
    *,
    top: float,
    lay: L,
    font_size: int,
    font_weight: str | int = "bold",
    fill: str,
    swibp_style: str = "heading",
    left: float | None = None,
    width: float | None = None,
) -> tuple[dict[str, Any], float]:
    x = lay.pad if left is None else left
    w = (lay.w - lay.pad * 2) if width is None else width
    h = text_h(text, font_size, w)
    obj = textbox(
        text,
        left=x,
        top=top,
        width=w,
        height=h,
        font_size=font_size,
        font_family=FONT,
        fill=fill,
        font_weight=font_weight,
        text_align="left",
        line_height=LINE_HEIGHT,
        swibp_style=swibp_style,
    )
    return obj, top + h


def items_text(items: list[str], *, bullet: str = "→") -> str:
    lines = []
    for raw in items:
        t = re.sub(r"^[\s→\-\d\.☐✓]+", "", (raw or "").strip())
        if t:
            lines.append(f"{bullet} {t}")
    return "\n".join(lines)


def stack_height(
    heading: str,
    body: str,
    items: list[str],
    callout: str,
    lay: L,
    *,
    bullet: str = "→",
    head_size: int = SIZE_HEAD,
    body_size: int = SIZE_BODY,
) -> float:
    width = lay.w - lay.pad * 2
    h = text_h(heading, head_size, width)
    if items:
        h += GAP + text_h(items_text(items, bullet=bullet), body_size, width)
    elif body:
        h += GAP + text_h(body, body_size, width)
    if callout:
        h += GAP + text_h(callout, body_size, width - 32) + 28
    return h


def content_start_y(
    total_h: float,
    lay: L,
    *,
    zone_top: float = 0,
    zone_bottom: float | None = None,
) -> float:
    bottom = zone_bottom if zone_bottom is not None else lay.h
    y = zone_top + (bottom - zone_top - total_h) / 2
    min_y = zone_top + (PHOTO_TEXT_GAP if zone_top > 0 else lay.pad * 1.8)
    max_y = bottom - total_h - lay.pad * 2.2
    return max(min_y, min(y, max_y))


def callout_block(
    text: str,
    *,
    top: float,
    lay: L,
    palette: Palette,
    label: str = "",
    left: float | None = None,
    width: float | None = None,
) -> tuple[list[dict[str, Any]], float]:
    x = lay.pad if left is None else left
    w = (lay.w - lay.pad * 2) if width is None else width
    pad_y = 14
    label_h = 22 if label else 0
    th = text_h(text, SIZE_BODY, w - 32) + pad_y * 2 + label_h
    objs: list[dict[str, Any]] = [
        rect(
            left=x,
            top=top,
            width=w,
            height=th,
            fill=palette.accent,
            rx=0,
            ry=0,
            swibp_slot="accent",
        ),
    ]
    y = top + pad_y
    if label:
        objs.append(
            textbox(
                label,
                left=x + 16,
                top=y,
                width=w - 32,
                font_size=SIZE_META,
                font_family=FONT,
                fill=palette.accent_text,
                font_weight="600",
                text_align="left",
                line_height=LINE_HEIGHT,
                swibp_style="body",
                swibp_slot="accent",
            )
        )
        y += label_h
    objs.append(
        textbox(
            text,
            left=x + 16,
            top=y,
            width=w - 32,
            height=th - (y - top) - pad_y,
            font_size=SIZE_BODY,
            font_family=FONT,
            fill=palette.accent_text,
            font_weight="700",
            text_align="left",
            line_height=LINE_HEIGHT,
            swibp_style="heading",
            swibp_slot="accent",
        )
    )
    return objs, top + th


def with_grid_for(index: int, total: int, grid_mode: str) -> bool:
    is_first = index == 0
    is_last = index == total - 1
    if grid_mode == "none":
        return False
    if grid_mode == "all":
        return True
    if grid_mode == "cover_only":
        return is_first
    return is_first or is_last


def meta_handle(
    handle: str,
    lay: L,
    *,
    fill: str,
    font_weight: str | int = "500",
) -> dict[str, Any]:
    return textbox(
        handle,
        left=lay.pad,
        top=lay.pad * 0.7,
        width=lay.w * 0.45,
        font_size=SIZE_META,
        font_family=FONT,
        fill=fill,
        font_weight=font_weight,
        text_align="left",
        line_height=LINE_HEIGHT,
        swibp_style="body",
        swibp_role="handle",
    )


class CarouselTemplate(ABC):
    """One visual system for a skill (or the default when skill is unset)."""

    skill_id: ClassVar[str | None] = None
    item_bullet: ClassVar[str] = "→"
    head_size: ClassVar[int] = SIZE_HEAD
    body_size: ClassVar[int] = SIZE_BODY

    def design_defaults(self) -> dict[str, Any]:
        return {"hasCover": True, "gridMode": "edges", "accentBias": 0.45, "photoRatio": 0.48}

    def merge_design(self, design: dict[str, Any] | None) -> dict[str, Any]:
        """Plan design + template defaults. Skill templates own visual knobs."""
        base = self.design_defaults()
        incoming = dict(design or {})
        merged = {**base, **incoming}
        if self.skill_id:
            for key in ("gridMode", "accentBias", "photoRatio"):
                if key in base:
                    merged[key] = base[key]
        return merged

    def resolve_layout(
        self,
        s: SlideContent,
        *,
        index: int,
        total: int,
        design: dict[str, Any],
        photo: str,
        rng: random.Random,
    ) -> str:
        has_cover = bool(design.get("hasCover", True))
        accent_bias = float(design.get("accentBias") or 0.45)
        is_last = index == total - 1
        layout = s.layout
        if index == 0:
            layout = "cover" if has_cover else ("statement" if layout == "cover" else layout)
        elif is_last:
            layout = "cta"
        elif photo:
            layout = "cover"
        elif layout == "orange_quote" and rng.random() > accent_bias:
            layout = "statement"
        return layout

    @abstractmethod
    def layout_cover(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
        with_grid: bool,
        cover_src: str,
        photo_ratio: float = 0.48,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def layout_content(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
        with_grid: bool,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def layout_accent_quote(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def layout_cta(
        self,
        s: SlideContent,
        lay: L,
        handle: str,
        category: str,
        palette: Palette,
        *,
        index: int,
        with_grid: bool,
    ) -> dict[str, Any]:
        raise NotImplementedError

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
        grid_mode = str(design.get("gridMode") or "edges")
        photo_ratio = float(design.get("photoRatio") or 0.48)
        with_grid = with_grid_for(index, total, grid_mode)
        photo = (slide_photo or "").strip() or ((cover_src or "").strip() if index == 0 else "")
        layout = self.resolve_layout(
            s, index=index, total=total, design=design, photo=photo, rng=rng
        )

        if layout == "cover":
            return self.layout_cover(
                s,
                lay,
                handle,
                category,
                palette,
                index=index,
                with_grid=with_grid,
                cover_src=photo,
                photo_ratio=photo_ratio,
            )
        if layout == "orange_quote":
            return self.layout_accent_quote(s, lay, handle, category, palette, index=index)
        if layout == "cta":
            return self.layout_cta(
                s, lay, handle, category, palette, index=index, with_grid=with_grid
            )
        return self.layout_content(
            s,
            lay,
            handle,
            category,
            palette,
            index=index,
            with_grid=with_grid and grid_mode == "all",
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
    ) -> dict[str, Any]:
        aspect = normalize_aspect(aspect_ratio)
        w, h = canvas_size(aspect)
        rng = random.Random(seed)
        lay = make_layout(w, h)
        handle = handle_text(content.handle)
        category = content.category.strip()
        if not category:
            raise RuntimeError("Не указан category.")
        total = len(content.slides)
        if total < 1:
            raise RuntimeError("Нет слайдов для сборки.")

        design = self.merge_design(design)
        cover_src = content.cover if design.get("hasCover") else ""
        photos = list(slide_photos or [])

        slides_out = [
            self.build_slide(
                s,
                index=i,
                total=total,
                lay=lay,
                handle=handle,
                category=category,
                cover_src=cover_src,
                palette=palette,
                rng=rng,
                design=design,
                slide_photo=photos[i] if i < len(photos) else "",
            )
            for i, s in enumerate(content.slides)
        ]

        return {
            "title": content.title,
            "aspectRatio": aspect,
            "width": w,
            "height": h,
            "design": design,
            "templateId": self.skill_id or "default",
            "slides": slides_out,
        }


# Re-export fabric primitives used by subclasses
__all__ = [
    "CarouselTemplate",
    "FONT",
    "GAP",
    "L",
    "LINE_HEIGHT",
    "PHOTO_TEXT_GAP",
    "SIZE_BODY",
    "SIZE_HEAD",
    "SIZE_META",
    "callout_block",
    "clip",
    "content_start_y",
    "counter",
    "footer",
    "grid",
    "handle_text",
    "image",
    "items_text",
    "make_layout",
    "meta_handle",
    "rect",
    "slide",
    "stack_height",
    "text_block",
    "text_h",
    "textbox",
]
