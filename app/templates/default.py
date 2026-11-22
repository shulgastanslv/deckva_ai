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
    cover_photo_frame,
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
        cover_placement: str = "top",
        cover_rounded: bool = False,
    ) -> dict[str, Any]:
        frame = cover_photo_frame(
            lay,
            placement=cover_placement,
            photo_ratio=photo_ratio,
            rounded=cover_rounded,
        )
        pl = float(frame["left"])
        pt = float(frame["top"])
        pw = float(frame["width"])
        ph = float(frame["height"])
        rx = float(frame.get("rx") or 0)
        ry = float(frame.get("ry") or 0)
        text_left = float(frame["text_left"])
        text_width = float(frame["text_width"])
        zone_top = float(frame["text_zone_top"])
        zone_bottom = float(frame["text_zone_bottom"])

        has_src = bool(cover_src.strip())
        if has_src:
            objs: list[dict[str, Any]] = [
                image(
                    cover_src.strip(),
                    left=pl,
                    top=pt,
                    width=pw,
                    height=ph,
                    swibp_slot="image",
                    rx=rx,
                    ry=ry,
                )
            ]
        else:
            objs = [
                rect(
                    left=pl,
                    top=pt,
                    width=pw,
                    height=ph,
                    fill=palette.photo,
                    rx=rx,
                    ry=ry,
                    swibp_slot="image",
                )
            ]

        place = cover_placement if cover_placement in ("top", "bottom", "left", "right") else "top"
        handle_on_photo = place in ("top", "left")
        counter_on_photo = place in ("top", "right")
        handle_fill = "#FFFFFF" if handle_on_photo else palette.text
        counter_fill = "#FFFFFF" if counter_on_photo else palette.text

        if with_grid:
            # Grid sits in the text zone so it stays editable as one canvas group.
            if place == "bottom":
                objs.extend(grid(lay.w, lay.h, lay.step, palette, top=0, height=max(1.0, zone_bottom)))
            elif place == "left":
                objs.extend(
                    grid(
                        lay.w,
                        lay.h,
                        lay.step,
                        palette,
                        left=text_left - lay.pad * 0.2,
                        top=0,
                        width=lay.w - (text_left - lay.pad * 0.2),
                        height=float(lay.h),
                    )
                )
            elif place == "right":
                objs.extend(
                    grid(
                        lay.w,
                        lay.h,
                        lay.step,
                        palette,
                        left=0,
                        top=0,
                        width=max(1.0, text_left + text_width + lay.pad * 0.2),
                        height=float(lay.h),
                    )
                )
            else:
                objs.extend(
                    grid(
                        lay.w,
                        lay.h,
                        lay.step,
                        palette,
                        top=zone_top - PHOTO_TEXT_GAP,
                        height=lay.h - (zone_top - PHOTO_TEXT_GAP),
                    )
                )

        objs.append(meta_handle(handle, lay, fill=handle_fill, font_weight="600"))
        objs.append(counter(index, lay, fill=counter_fill))

        heading = clip(s.heading, 120)
        body = clip(s.body, 200) if s.body else ""
        total_h = stack_height(
            heading,
            body,
            [],
            "",
            lay,
            head_size=self.head_px,
            body_size=self.body_px,
            width=text_width,
        )
        y = content_start_y(total_h, lay, zone_top=zone_top, zone_bottom=zone_bottom)
        y = max(y, zone_top)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_px,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
            left=text_left,
            width=text_width,
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
                left=text_left,
                width=text_width,
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
