"""Shared layout helpers + abstract carousel template."""

from __future__ import annotations

import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from app.fabric import canvas_size, group, image, normalize_aspect, rect, slide, textbox
from app.fonts import (
    Typography,
    current_font,
    current_typography,
    push_typography,
    reset_typography,
    scaled_size,
)
from app.palette import Palette
from app.schemas import CarouselContent, SlideContent

# Back-compat alias: prefer current_font() / scaled_size()
FONT = "Montserrat"
SIZE_HEAD = 55
SIZE_BODY = 25
SIZE_META = 20
GAP = 20
LINE_HEIGHT = 0.90
# Faint decorative canvas grid — edit as one Group (swibpRole=canvas).
GRID_OPACITY = 0.07
PHOTO_TEXT_GAP = 2
COVER_PLACEMENTS = ("top", "bottom", "left", "right")
COVER_ROUNDED_CHANCE = 0.30


def _font() -> str:
    return current_font()


def _meta_size() -> int:
    return current_typography().meta_size


def _body_size() -> int:
    return current_typography().body_size


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
    h = (h or "").strip()
    if not current_typography().show_handle:
        if not h:
            return ""
        return h if h.startswith("@") else f"@{h}"
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


def split_stack(text: str, *, max_lines: int = 6) -> list[str]:
    """Split words into ≤ max_lines for stacked cover titles."""
    words = [w for w in (text or "").split() if w]
    if not words:
        return [""]
    if len(words) <= max_lines:
        return words
    n = max_lines
    out: list[str] = []
    i = 0
    for line_i in range(n):
        left = n - line_i
        take = max(1, round((len(words) - i) / left))
        chunk = words[i : i + take]
        if not chunk:
            break
        out.append(" ".join(chunk))
        i += take
    if i < len(words):
        out[-1] = (out[-1] + " " + " ".join(words[i:])).strip()
    return out


def full_bleed_photo(
    lay: L,
    cover_src: str,
    palette: Palette,
    *,
    dim: float = 0.22,
) -> list[dict[str, Any]]:
    """Full-canvas photo (or palette placeholder) with optional darken overlay."""
    if (cover_src or "").strip():
        objs: list[dict[str, Any]] = [
            image(cover_src.strip(), left=0, top=0, width=lay.w, height=lay.h, swibp_slot="image")
        ]
        if dim > 0:
            objs.append(
                rect(
                    left=0,
                    top=0,
                    width=lay.w,
                    height=lay.h,
                    fill="#000000",
                    opacity=dim,
                    swibp_slot="accent",
                )
            )
        return objs
    return [rect(left=0, top=0, width=lay.w, height=lay.h, fill=palette.photo, swibp_slot="image")]


def grid(
    w: int,
    h: int,
    step: float,
    palette: Palette,
    *,
    top: float = 0,
    height: float | None = None,
    left: float = 0,
    width: float | None = None,
) -> list[dict[str, Any]]:
    """One editable canvas Group (not a pile of loose lines)."""
    ww = float(width) if width is not None else float(w) - left
    hh = float(height) if height is not None else float(h) - top
    if ww <= 1 or hh <= 1 or step <= 0:
        return []

    lines: list[dict[str, Any]] = []
    x = 0.0
    while x <= ww + 0.5:
        lines.append(
            rect(
                left=x,
                top=0,
                width=1.2,
                height=hh,
                fill=palette.grid,
                opacity=1.0,
                swibp_slot="accent",
            )
        )
        x += step
    y = 0.0
    while y <= hh + 0.5:
        lines.append(
            rect(
                left=0,
                top=y,
                width=ww,
                height=1.2,
                fill=palette.grid,
                opacity=1.0,
                swibp_slot="accent",
            )
        )
        y += step

    return [
        group(
            lines,
            left=left,
            top=top,
            width=ww,
            height=hh,
            opacity=GRID_OPACITY,
            swibp_role="canvas",
            swibp_name="Canvas",
            swibp_slot="accent",
        )
    ]


def counter(index: int, lay: L, *, fill: str) -> dict[str, Any]:
    meta = _meta_size()
    return textbox(
        f"( {index + 1} )",
        left=lay.w - lay.pad - 140,
        top=lay.pad * 0.7,
        width=140,
        font_size=meta,
        font_family=_font(),
        fill=fill,
        font_weight="600",
        text_align="right",
        line_height=LINE_HEIGHT,
        swibp_style="body",
        swibp_role="counter",
    )


def footer(lay: L, category: str, *, fill_cat: str, fill_arrow: str) -> list[dict[str, Any]]:
    meta = _meta_size()
    return [
        textbox(
            clip(category, 24),
            left=lay.pad,
            top=lay.h - lay.pad - meta,
            width=lay.w * 0.45,
            font_size=meta,
            font_family=_font(),
            fill=fill_cat,
            font_weight="500",
            text_align="left",
            line_height=LINE_HEIGHT,
            swibp_style="body",
        ),
        textbox(
            "→",
            left=lay.w - lay.pad - 48,
            top=lay.h - lay.pad - meta - 4,
            width=48,
            font_size=32,
            font_family=_font(),
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
        font_family=_font(),
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
    width: float | None = None,
) -> float:
    text_w = float(width) if width is not None else lay.w - lay.pad * 2
    h = text_h(heading, head_size, text_w)
    if items:
        h += GAP + text_h(items_text(items, bullet=bullet), body_size, text_w)
    elif body:
        h += GAP + text_h(body, body_size, text_w)
    if callout:
        h += GAP + text_h(callout, body_size, max(40.0, text_w - 32)) + 28
    return h


def pick_cover_style(rng: random.Random, design: dict[str, Any] | None = None) -> tuple[str, bool]:
    """Placement + optional floating rounded cover (not edge-flush)."""
    design = design or {}
    placement = str(design.get("coverPlacement") or "").strip().lower()
    if placement not in COVER_PLACEMENTS:
        placement = rng.choice(COVER_PLACEMENTS)
    if "coverRounded" in design:
        rounded = bool(design.get("coverRounded"))
    else:
        rounded = rng.random() < COVER_ROUNDED_CHANCE
    return placement, rounded


def cover_photo_frame(
    lay: L,
    *,
    placement: str,
    photo_ratio: float,
    rounded: bool,
) -> dict[str, float]:
    """Geometry for cover image + text zone.

    Returns photo box + text_* keys (left/width/zone_top/zone_bottom) + rx/ry.
    """
    ratio = max(0.32, min(0.58, float(photo_ratio or 0.48)))
    inset = (lay.pad * 0.9) if rounded else 0.0
    radius = 32.0 if rounded else 0.0
    place = placement if placement in COVER_PLACEMENTS else "top"

    if place == "bottom":
        photo_h = lay.h * ratio
        if rounded:
            photo = {
                "left": inset,
                "top": lay.h - photo_h,
                "width": lay.w - inset * 2,
                "height": photo_h - inset,
            }
        else:
            photo = {"left": 0.0, "top": lay.h - photo_h, "width": float(lay.w), "height": photo_h}
        text = {
            "left": lay.pad,
            "width": lay.w - lay.pad * 2,
            "zone_top": lay.pad * 1.2,
            "zone_bottom": photo["top"] - PHOTO_TEXT_GAP,
        }
    elif place == "left":
        photo_w = lay.w * ratio
        if rounded:
            photo = {
                "left": inset,
                "top": inset,
                "width": max(80.0, photo_w - inset),
                "height": lay.h - inset * 2,
            }
            text_left = photo["left"] + photo["width"] + PHOTO_TEXT_GAP + lay.pad * 0.35
        else:
            photo = {"left": 0.0, "top": 0.0, "width": photo_w, "height": float(lay.h)}
            text_left = photo_w + PHOTO_TEXT_GAP + lay.pad * 0.25
        text = {
            "left": text_left,
            "width": max(120.0, lay.w - text_left - lay.pad),
            "zone_top": lay.pad * 1.8,
            "zone_bottom": float(lay.h),
        }
    elif place == "right":
        photo_w = lay.w * ratio
        if rounded:
            photo = {
                "left": lay.w - photo_w,
                "top": inset,
                "width": max(80.0, photo_w - inset),
                "height": lay.h - inset * 2,
            }
            text_right = photo["left"] - PHOTO_TEXT_GAP - lay.pad * 0.35
        else:
            photo = {"left": lay.w - photo_w, "top": 0.0, "width": photo_w, "height": float(lay.h)}
            text_right = photo["left"] - PHOTO_TEXT_GAP - lay.pad * 0.25
        text = {
            "left": lay.pad,
            "width": max(120.0, text_right - lay.pad),
            "zone_top": lay.pad * 1.8,
            "zone_bottom": float(lay.h),
        }
    else:  # top
        photo_h = lay.h * ratio
        if rounded:
            photo = {
                "left": inset,
                "top": inset,
                "width": lay.w - inset * 2,
                "height": max(80.0, photo_h - inset),
            }
        else:
            photo = {"left": 0.0, "top": 0.0, "width": float(lay.w), "height": photo_h}
        text = {
            "left": lay.pad,
            "width": lay.w - lay.pad * 2,
            "zone_top": photo["top"] + photo["height"] + PHOTO_TEXT_GAP,
            "zone_bottom": float(lay.h),
        }

    photo["rx"] = radius
    photo["ry"] = radius
    return {**photo, **{f"text_{k}": v for k, v in text.items()}}


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
    body = _body_size()
    meta = _meta_size()
    label_h = 22 if label else 0
    th = text_h(text, body, w - 32) + pad_y * 2 + label_h
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
                font_size=meta,
                font_family=_font(),
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
            font_size=body,
            font_family=_font(),
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
    """Grid is sparse by design — never every mid slide."""
    is_first = index == 0
    is_last = index == total - 1
    if grid_mode == "none":
        return False
    if grid_mode == "cover_only":
        return is_first
    if grid_mode == "cta_only":
        return is_last
    # "edges" (default) and legacy "all" → first + last only
    return is_first or is_last


def meta_handle(
    handle: str,
    lay: L,
    *,
    fill: str,
    font_weight: str | int = "500",
) -> dict[str, Any]:
    return textbox(
        handle or "",
        left=lay.pad,
        top=lay.pad * 0.7,
        width=lay.w * 0.45,
        font_size=_meta_size(),
        font_family=_font(),
        fill=fill,
        font_weight=font_weight,
        text_align="left",
        line_height=LINE_HEIGHT,
        swibp_style="body",
        swibp_role="handle",
    )


def _strip_handles(slide_obj: dict[str, Any]) -> dict[str, Any]:
    if current_typography().show_handle:
        return slide_obj
    objs = slide_obj.get("objects") or []
    slide_obj["objects"] = [o for o in objs if o.get("swibpRole") != "handle"]
    return slide_obj


class CarouselTemplate(ABC):
    """One visual system for a skill (or the default when skill is unset)."""

    skill_id: ClassVar[str | None] = None
    item_bullet: ClassVar[str] = "→"
    head_size: ClassVar[int] = SIZE_HEAD
    body_size: ClassVar[int] = SIZE_BODY

    @property
    def head_px(self) -> int:
        return scaled_size(type(self).head_size, kind="head")

    @property
    def body_px(self) -> int:
        return scaled_size(type(self).body_size, kind="body")

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
        cover_placement: str = "top",
        cover_rounded: bool = False,
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
            cover_placement, cover_rounded = pick_cover_style(rng, design)
            out = self.layout_cover(
                s,
                lay,
                handle,
                category,
                palette,
                index=index,
                with_grid=with_grid,
                cover_src=photo,
                photo_ratio=photo_ratio,
                cover_placement=cover_placement,
                cover_rounded=cover_rounded,
            )
        elif layout == "orange_quote":
            out = self.layout_accent_quote(s, lay, handle, category, palette, index=index)
        elif layout == "cta":
            out = self.layout_cta(
                s, lay, handle, category, palette, index=index, with_grid=with_grid
            )
        else:
            # Mid slides: grid only on edges/cta — never stamp every content slide
            out = self.layout_content(
                s,
                lay,
                handle,
                category,
                palette,
                index=index,
                with_grid=False,
            )
        return _strip_handles(out)

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
        aspect = normalize_aspect(aspect_ratio)
        w, h = canvas_size(aspect)
        rng = random.Random(seed)
        lay = make_layout(w, h)
        design = self.merge_design(design)
        typo = typography
        if typo is None and isinstance(design.get("typography"), dict):
            from app.fonts import parse_typography

            typo = parse_typography(
                design["typography"],
                show_handle=bool(design.get("showHandle", True)),
            )
        if typo is None:
            typo = current_typography()

        token = push_typography(typo)
        try:
            handle = handle_text(content.handle)
            category = content.category.strip()
            if not category:
                raise RuntimeError("Не указан category.")
            total = len(content.slides)
            if total < 1:
                raise RuntimeError("Нет слайдов для сборки.")

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

            design = {
                **design,
                "typography": typo.to_dict(),
                "fontFamily": typo.font_family,
                "showHandle": typo.show_handle,
            }

            return {
                "title": content.title,
                "aspectRatio": aspect,
                "width": w,
                "height": h,
                "design": design,
                "typography": typo.to_dict(),
                "templateId": self.skill_id or "default",
                "slides": slides_out,
            }
        finally:
            reset_typography(token)


# Re-export fabric primitives used by subclasses
__all__ = [
    "COVER_PLACEMENTS",
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
    "cover_photo_frame",
    "current_font",
    "footer",
    "full_bleed_photo",
    "grid",
    "group",
    "handle_text",
    "image",
    "items_text",
    "make_layout",
    "meta_handle",
    "pick_cover_style",
    "rect",
    "scaled_size",
    "slide",
    "split_stack",
    "stack_height",
    "text_block",
    "text_h",
    "textbox",
]
