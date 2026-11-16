"""Reference visual skills — full-bleed lifestyle covers inspired by blog carousels."""

from __future__ import annotations

from typing import Any, ClassVar

from app.palette import Palette
from app.schemas import SlideContent
from app.templates.base import (
    FONT,
    GAP,
    SIZE_META,
    L,
    clip,
    counter,
    footer,
    image,
    meta_handle,
    rect,
    slide,
    text_block,
    text_h,
    textbox,
)
from app.templates.default import DefaultTemplate


def _full_bleed_photo(
    lay: L,
    cover_src: str,
    palette: Palette,
    *,
    dim: float = 0.28,
) -> list[dict[str, Any]]:
    """Edge-to-edge photo (+ optional dark scrim for type)."""
    if cover_src.strip():
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


def _split_stack(text: str, *, max_lines: int = 6) -> list[str]:
    words = [w for w in (text or "").split() if w]
    if not words:
        return [""]
    if len(words) <= max_lines:
        return words
    # pack into max_lines roughly evenly
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


class AestheticTemplate(DefaultTemplate):
    """Ref: moody full-bleed + lowercase copy bottom-left + ( → ) swipe hint."""

    skill_id: ClassVar[str | None] = "aesthetic"
    head_size: ClassVar[int] = 36

    def design_defaults(self) -> dict[str, Any]:
        return {
            **super().design_defaults(),
            "photoRatio": 1.0,
            "gridMode": "none",
            "accentBias": 0.2,
            "hasCover": True,
        }

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
        photo_ratio: float = 1.0,
    ) -> dict[str, Any]:
        objs = _full_bleed_photo(lay, cover_src, palette, dim=0.22)
        fill = "#FFFFFF"
        objs.append(meta_handle(handle, lay, fill=fill, font_weight="500"))
        objs.append(
            textbox(
                "( → )",
                left=lay.pad,
                top=lay.h * 0.58,
                width=120,
                font_size=SIZE_META,
                font_family=FONT,
                fill=fill,
                font_weight="400",
                opacity=0.85,
                swibp_style="body",
            )
        )
        heading = clip(s.heading, 160).lower()
        body = clip(s.body, 100).lower() if s.body else ""
        head_h = text_h(heading, self.head_size, lay.w * 0.62)
        body_h = text_h(body, 22, lay.w * 0.55) if body else 0
        y = lay.h - lay.pad * 2.2 - head_h - (GAP + body_h if body else 0)
        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_size,
            font_weight="500",
            fill=fill,
            swibp_style="heading",
            width=lay.w * 0.62,
        )
        objs.append(head)
        if body:
            b, _ = text_block(
                body,
                top=bottom + 10,
                lay=lay,
                font_size=22,
                font_weight="700",
                fill=fill,
                swibp_style="body",
                width=lay.w * 0.55,
            )
            objs.append(b)
        objs.extend(footer(lay, category, fill_cat=fill, fill_arrow=fill))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class ManifestoTemplate(DefaultTemplate):
    """Ref: full-bleed portrait + huge stacked centered statement."""

    skill_id: ClassVar[str | None] = "manifesto"
    head_size: ClassVar[int] = 64

    def design_defaults(self) -> dict[str, Any]:
        return {
            **super().design_defaults(),
            "photoRatio": 1.0,
            "gridMode": "none",
            "accentBias": 0.15,
            "hasCover": True,
        }

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
        photo_ratio: float = 1.0,
    ) -> dict[str, Any]:
        objs = _full_bleed_photo(lay, cover_src, palette, dim=0.18)
        fill = "#FFFFFF"
        objs.append(
            textbox(
                handle,
                left=lay.pad,
                top=lay.pad * 0.9,
                width=lay.w * 0.45,
                font_size=SIZE_META,
                font_family=FONT,
                fill=fill,
                font_weight="500",
                swibp_style="body",
                swibp_role="handle",
            )
        )
        objs.append(counter(index, lay, fill=fill))

        lines = _split_stack(clip(s.heading, 80).upper(), max_lines=5)
        line_size = self.head_size
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
                    font_family=FONT,
                    fill=fill,
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
                    left=lay.w * 0.42,
                    top=lay.h - lay.pad * 2.4,
                    width=lay.w * 0.5,
                    font_size=18,
                    font_family=FONT,
                    fill="#111111",
                    font_weight="500",
                    swibp_style="body",
                )
            )
        objs.extend(footer(lay, category, fill_cat=fill, fill_arrow=fill))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class NichesTemplate(DefaultTemplate):
    """Ref: lifestyle cover + floating niche tags (items) + bracketed title."""

    skill_id: ClassVar[str | None] = "niches"
    head_size: ClassVar[int] = 42

    def design_defaults(self) -> dict[str, Any]:
        return {
            **super().design_defaults(),
            "photoRatio": 1.0,
            "gridMode": "none",
            "accentBias": 0.25,
            "hasCover": True,
        }

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
        photo_ratio: float = 1.0,
    ) -> dict[str, Any]:
        objs = _full_bleed_photo(lay, cover_src, palette, dim=0.12)
        cream = "#F2E6A8"
        white = "#FFFFFF"

        title = clip(s.heading, 48)
        objs.append(
            textbox(
                f"[ {title.lower()} ]",
                left=lay.pad,
                top=lay.pad * 1.1,
                width=lay.w - lay.pad * 2,
                font_size=28,
                font_family=FONT,
                fill=cream,
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
                    font_family=FONT,
                    fill=cream,
                    font_weight="600",
                    swibp_style="body",
                )
            )

        # Floating tags from items — left / right columns around center
        tags = [clip(t, 22).lower() for t in (s.items or [])[:8] if str(t).strip()]
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
                    font_family=FONT,
                    fill=cream,
                    font_weight="700",
                    swibp_style="body",
                )
            )
            if on_left:
                y_left += 52
            else:
                y_right += 56

        sub = clip(s.callout or "", 60)
        if sub:
            objs.append(
                textbox(
                    sub.lower(),
                    left=lay.w * 0.42,
                    top=lay.h - lay.pad * 3.2,
                    width=lay.w * 0.5,
                    font_size=22,
                    font_family=FONT,
                    fill=cream,
                    font_weight="600",
                    text_align="right",
                    swibp_style="body",
                )
            )

        objs.append(
            textbox(
                handle,
                left=lay.w - lay.pad - 200,
                top=lay.h - lay.pad * 1.4,
                width=200,
                font_size=SIZE_META,
                font_family=FONT,
                fill=white,
                font_weight="500",
                text_align="right",
                swibp_style="body",
                swibp_role="handle",
            )
        )
        objs.extend(footer(lay, category, fill_cat=white, fill_arrow=cream))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class LookbookTemplate(DefaultTemplate):
    """Ref: fashion/lifestyle full-bleed + centered idea title + /save/ cue."""

    skill_id: ClassVar[str | None] = "lookbook"
    head_size: ClassVar[int] = 48

    def design_defaults(self) -> dict[str, Any]:
        return {
            **super().design_defaults(),
            "photoRatio": 1.0,
            "gridMode": "none",
            "accentBias": 0.2,
            "hasCover": True,
        }

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
        photo_ratio: float = 1.0,
    ) -> dict[str, Any]:
        objs = _full_bleed_photo(lay, cover_src, palette, dim=0.2)
        cream = "#EDE4D0"
        fill = "#FFFFFF"

        objs.append(
            textbox(
                clip(s.tag or category, 48).lower(),
                left=lay.pad,
                top=lay.pad,
                width=lay.w * 0.55,
                font_size=16,
                font_family=FONT,
                fill=fill,
                font_weight="500",
                opacity=0.9,
                swibp_style="body",
            )
        )
        objs.append(
            textbox(
                handle,
                left=lay.w - lay.pad - 180,
                top=lay.pad,
                width=180,
                font_size=SIZE_META,
                font_family=FONT,
                fill=fill,
                font_weight="500",
                text_align="right",
                swibp_style="body",
                swibp_role="handle",
            )
        )

        heading = clip(s.heading, 90).lower()
        head_h = text_h(heading, self.head_size, lay.w - lay.pad * 2)
        y = lay.h * 0.42 - head_h / 2
        objs.append(
            textbox(
                heading,
                left=lay.pad,
                top=y,
                width=lay.w - lay.pad * 2,
                font_size=self.head_size,
                font_family=FONT,
                fill=cream,
                font_weight="700",
                text_align="center",
                line_height=0.95,
                swibp_style="heading",
            )
        )
        cue = clip(s.callout or s.body or "сохраняй", 28).lower().strip("/")
        objs.append(
            textbox(
                f"/{cue}/",
                left=lay.pad,
                top=y + head_h + 16,
                width=lay.w - lay.pad * 2,
                font_size=20,
                font_family=FONT,
                fill=fill,
                font_weight="500",
                text_align="center",
                swibp_style="body",
            )
        )
        objs.extend(footer(lay, category, fill_cat=fill, fill_arrow=cream))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


REFERENCE_SKILL_TEMPLATE_CLASSES: list[type[DefaultTemplate]] = [
    AestheticTemplate,
    ManifestoTemplate,
    NichesTemplate,
    LookbookTemplate,
]
