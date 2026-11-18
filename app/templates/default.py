"""Default carousel template — used when no skill is selected."""

from __future__ import annotations

from typing import Any, ClassVar

from app.palette import Palette
from app.schemas import SlideContent
from app.templates.base import (
    GAP,
    PHOTO_TEXT_GAP,
    CarouselTemplate,
    L,
    callout_block,
    clip,
    content_start_y,
    counter,
    footer,
    grid,
    image,
    items_text,
    meta_handle,
    rect,
    slide,
    stack_height,
    text_block,
)


class DefaultTemplate(CarouselTemplate):
    """Left-align, vertical center, edge grid — original Deckva assemble."""

    skill_id: ClassVar[str | None] = None

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
        ratio = max(0.32, min(0.58, float(photo_ratio or 0.48)))
        photo_h = lay.h * ratio
        if cover_src.strip():
            objs: list[dict[str, Any]] = [
                image(cover_src.strip(), left=0, top=0, width=lay.w, height=photo_h, swibp_slot="image")
            ]
            handle_fill = "#FFFFFF"
            counter_fill = "#FFFFFF"
        else:
            objs = [rect(left=0, top=0, width=lay.w, height=photo_h, fill=palette.photo, swibp_slot="image")]
            handle_fill = palette.text
            counter_fill = palette.text

        if with_grid:
            objs.extend(grid(lay.w, lay.h, lay.step, palette, top=photo_h, height=lay.h - photo_h))

        objs.append(meta_handle(handle, lay, fill=handle_fill, font_weight="600"))
        objs.append(counter(index, lay, fill=counter_fill))

        heading = clip(s.heading, 120)
        body = clip(s.body, 200) if s.body else ""
        total_h = stack_height(
            heading, body, [], "", lay, head_size=self.head_px, body_size=self.body_px
        )
        y = content_start_y(total_h, lay, zone_top=photo_h + PHOTO_TEXT_GAP, zone_bottom=lay.h)
        y = max(y, photo_h + PHOTO_TEXT_GAP)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_px,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)
        if body:
            b, _ = text_block(
                body,
                top=bottom + GAP,
                lay=lay,
                font_size=self.body_px,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(b)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)

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
        objs: list[dict[str, Any]] = []
        if with_grid:
            objs.extend(grid(lay.w, lay.h, lay.step, palette))

        objs.append(meta_handle(handle, lay, fill=palette.text))
        objs.append(counter(index, lay, fill=palette.text))

        heading = clip(s.heading, 140)
        body = clip(s.body, 220) if s.body else ""
        items = s.items or []
        callout = clip(s.callout, 140) if s.callout else ""
        total_h = stack_height(
            heading,
            body,
            items,
            callout,
            lay,
            bullet=self.item_bullet,
            head_size=self.head_px,
            body_size=self.body_px,
        )
        y = content_start_y(total_h, lay)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_px,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)

        next_top = bottom + GAP
        if items:
            block, bottom = text_block(
                items_text(items, bullet=self.item_bullet),
                top=next_top,
                lay=lay,
                font_size=self.body_px,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)
            next_top = bottom + GAP
        elif body:
            block, bottom = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_px,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)
            next_top = bottom + GAP

        if callout:
            call_objs, _ = callout_block(callout, top=next_top, lay=lay, palette=palette)
            objs.extend(call_objs)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)

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
        objs: list[dict[str, Any]] = [
            meta_handle(handle, lay, fill=palette.accent_text),
            counter(index, lay, fill=palette.accent_text),
        ]
        heading = clip(s.heading, 180)
        total_h = stack_height(heading, "", [], "", lay, head_size=self.head_px)
        y = content_start_y(total_h, lay)
        head, _ = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_px,
            font_weight="bold",
            fill=palette.accent_text,
            swibp_style="heading",
        )
        objs.append(head)
        objs.extend(footer(lay, category, fill_cat=palette.accent_text, fill_arrow=palette.accent_text))
        return slide(palette.accent, objs, width=lay.w, height=lay.h)

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
        objs: list[dict[str, Any]] = []
        if with_grid:
            objs.extend(grid(lay.w, lay.h, lay.step, palette))

        objs.append(meta_handle(handle, lay, fill=palette.text))
        objs.append(counter(index, lay, fill=palette.text))

        heading = clip(s.callout or s.heading, 140)
        body = clip(s.body, 160) if s.body else ""
        total_h = stack_height(
            heading, body, [], "", lay, head_size=self.head_px, body_size=self.body_px
        )
        y = content_start_y(total_h, lay)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_px,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)
        if body:
            b, _ = text_block(
                body,
                top=bottom + GAP,
                lay=lay,
                font_size=self.body_px,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(b)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)
