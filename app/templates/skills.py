"""Skill-specific visual templates. Subclass DefaultTemplate and override layouts."""

from __future__ import annotations

from typing import Any, ClassVar

from app.palette import Palette
from app.schemas import SlideContent
from app.templates.base import (
    FONT,
    GAP,
    LINE_HEIGHT,
    SIZE_BODY,
    SIZE_META,
    L,
    callout_block,
    clip,
    content_start_y,
    counter,
    footer,
    grid,
    items_text,
    meta_handle,
    rect,
    slide,
    stack_height,
    text_block,
    text_h,
    textbox,
)
from app.templates.default import DefaultTemplate


class LaunchTemplate(DefaultTemplate):
    """Product launch: taller hero photo, accent rule under headline, bold CTA bar."""

    skill_id: ClassVar[str | None] = "launch"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "photoRatio": 0.52, "accentBias": 0.35, "gridMode": "edges"}

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
        photo_ratio: float = 0.52,
    ) -> dict[str, Any]:
        out = super().layout_cover(
            s,
            lay,
            handle,
            category,
            palette,
            index=index,
            with_grid=with_grid,
            cover_src=cover_src,
            photo_ratio=photo_ratio,
        )
        # Accent rule under first heading textbox
        heads = [o for o in out["objects"] if o.get("swibpStyle") == "heading"]
        if heads:
            h = heads[0]
            out["objects"].append(
                rect(
                    left=h["left"],
                    top=h["top"] + h["height"] + 10,
                    width=min(120.0, lay.w * 0.18),
                    height=6,
                    fill=palette.accent,
                    swibp_slot="accent",
                )
            )
        return out

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

        heading = clip(s.callout or s.heading, 120)
        body = clip(s.body, 140) if s.body else ""
        bar_h = text_h(heading, self.head_size, lay.w - lay.pad * 2 - 48) + 48
        body_h = (GAP + text_h(body, self.body_size, lay.w - lay.pad * 2)) if body else 0
        total_h = bar_h + body_h
        y = content_start_y(total_h, lay)

        objs.append(
            rect(
                left=lay.pad,
                top=y,
                width=lay.w - lay.pad * 2,
                height=bar_h,
                fill=palette.accent,
                swibp_slot="accent",
            )
        )
        head, _ = text_block(
            heading,
            top=y + 24,
            lay=lay,
            font_size=self.head_size,
            font_weight="bold",
            fill=palette.accent_text,
            swibp_style="heading",
            left=lay.pad + 24,
            width=lay.w - lay.pad * 2 - 48,
        )
        objs.append(head)
        if body:
            b, _ = text_block(
                body,
                top=y + bar_h + GAP,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(b)
        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class HowtoTemplate(DefaultTemplate):
    """How-to: large step index watermark, step-first content stack."""

    skill_id: ClassVar[str | None] = "howto"
    item_bullet: ClassVar[str] = "→"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.2, "gridMode": "none", "photoRatio": 0.42}

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

        # Large step watermark (mid slides only; cover/cta keep normal counter)
        step_n = max(1, index)
        objs.append(
            textbox(
                f"{step_n:02d}",
                left=lay.pad,
                top=lay.h * 0.22,
                width=lay.w * 0.55,
                font_size=160,
                font_family=FONT,
                fill=palette.grid,
                font_weight="700",
                text_align="left",
                line_height=0.85,
                opacity=0.55,
                swibp_style="body",
            )
        )
        objs.append(meta_handle(handle, lay, fill=palette.text))
        objs.append(counter(index, lay, fill=palette.text))

        heading = clip(s.heading, 120)
        body = clip(s.body, 200) if s.body else ""
        items = s.items or []
        callout = clip(s.callout, 120) if s.callout else ""
        total_h = stack_height(
            heading, body, items, callout, lay, bullet=self.item_bullet, head_size=48, body_size=self.body_size
        )
        y = content_start_y(total_h, lay)

        label, _ = text_block(
            f"STEP {step_n}",
            top=y,
            lay=lay,
            font_size=SIZE_META,
            font_weight="600",
            fill=palette.accent,
            swibp_style="body",
        )
        objs.append(label)
        head, bottom = text_block(
            heading,
            top=y + SIZE_META + 12,
            lay=lay,
            font_size=48,
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
                font_size=self.body_size,
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
                font_size=self.body_size,
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


class OfferTemplate(DefaultTemplate):
    """Offer: accent left rail + problem/solution callout emphasis."""

    skill_id: ClassVar[str | None] = "offer"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.55, "gridMode": "cover_only", "photoRatio": 0.46}

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
        objs: list[dict[str, Any]] = [
            rect(
                left=0,
                top=0,
                width=14,
                height=lay.h,
                fill=palette.accent,
                swibp_slot="accent",
            )
        ]
        if with_grid:
            objs.extend(grid(lay.w, lay.h, lay.step, palette))

        objs.append(meta_handle(handle, lay, fill=palette.text))
        objs.append(counter(index, lay, fill=palette.text))

        heading = clip(s.heading, 130)
        body = clip(s.body, 200) if s.body else ""
        items = s.items or []
        callout = clip(s.callout, 140) if s.callout else ""
        # Shift content right of rail
        inset = 18
        total_h = stack_height(
            heading, body, items, callout, lay, bullet=self.item_bullet, head_size=self.head_size, body_size=self.body_size
        )
        y = content_start_y(total_h, lay)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_size,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
            left=lay.pad + inset,
            width=lay.w - lay.pad * 2 - inset,
        )
        objs.append(head)
        next_top = bottom + GAP
        content_left = lay.pad + inset
        content_w = lay.w - lay.pad * 2 - inset
        if items:
            block, bottom = text_block(
                items_text(items, bullet=self.item_bullet),
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
                left=content_left,
                width=content_w,
            )
            objs.append(block)
            next_top = bottom + GAP
        elif body:
            block, bottom = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
                left=content_left,
                width=content_w,
            )
            objs.append(block)
            next_top = bottom + GAP
        if callout:
            call_objs, _ = callout_block(
                callout,
                top=next_top,
                lay=lay,
                palette=palette,
                label="OFFER",
                left=content_left,
                width=content_w,
            )
            objs.extend(call_objs)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.accent))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class TipsTemplate(DefaultTemplate):
    """Tips: oversized tip index + compact tip body."""

    skill_id: ClassVar[str | None] = "tips"
    head_size: ClassVar[int] = 48

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.15, "gridMode": "none", "photoRatio": 0.4}

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
        tip_n = max(1, index)
        objs.append(
            textbox(
                f"TIP {tip_n:02d}",
                left=lay.pad,
                top=lay.pad * 2.2,
                width=lay.w - lay.pad * 2,
                font_size=SIZE_META,
                font_family=FONT,
                fill=palette.accent,
                font_weight="700",
                text_align="left",
                line_height=LINE_HEIGHT,
                swibp_style="body",
                swibp_slot="accent",
            )
        )
        objs.append(meta_handle(handle, lay, fill=palette.text))
        objs.append(counter(index, lay, fill=palette.text))

        heading = clip(s.heading, 110)
        body = clip(s.body, 240) if s.body else ""
        items = s.items or []
        total_h = stack_height(heading, body, items, "", lay, head_size=self.head_size, body_size=self.body_size)
        y = content_start_y(total_h, lay, zone_top=lay.pad * 3.2)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_size,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)
        next_top = bottom + GAP
        if items:
            block, _ = text_block(
                items_text(items, bullet=self.item_bullet),
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)
        elif body:
            block, _ = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class StoryTemplate(DefaultTemplate):
    """Story / case: editorial quote bias, left accent spine on quotes."""

    skill_id: ClassVar[str | None] = "story"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.75, "gridMode": "none", "photoRatio": 0.5}

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
            textbox(
                "“",
                left=lay.pad,
                top=lay.h * 0.28,
                width=120,
                font_size=120,
                font_family=FONT,
                fill=palette.accent_text,
                font_weight="700",
                text_align="left",
                line_height=0.8,
                opacity=0.35,
                swibp_style="body",
            ),
        ]
        heading = clip(s.heading, 200)
        total_h = stack_height(heading, "", [], "", lay, head_size=50)
        y = content_start_y(total_h, lay)
        head, _ = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=50,
            font_weight="bold",
            fill=palette.accent_text,
            swibp_style="heading",
        )
        objs.append(head)
        objs.extend(footer(lay, category, fill_cat=palette.accent_text, fill_arrow=palette.accent_text))
        return slide(palette.accent, objs, width=lay.w, height=lay.h)

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
        objs: list[dict[str, Any]] = [
            rect(
                left=lay.pad,
                top=lay.pad * 2.4,
                width=4,
                height=lay.h - lay.pad * 4.8,
                fill=palette.accent,
                swibp_slot="accent",
            )
        ]
        if with_grid:
            objs.extend(grid(lay.w, lay.h, lay.step, palette))
        objs.append(meta_handle(handle, lay, fill=palette.text))
        objs.append(counter(index, lay, fill=palette.text))

        heading = clip(s.heading, 140)
        body = clip(s.body, 220) if s.body else ""
        items = s.items or []
        callout = clip(s.callout, 120) if s.callout else ""
        inset = 28
        total_h = stack_height(heading, body, items, callout, lay, head_size=self.head_size, body_size=self.body_size)
        y = content_start_y(total_h, lay)
        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_size,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
            left=lay.pad + inset,
            width=lay.w - lay.pad * 2 - inset,
        )
        objs.append(head)
        next_top = bottom + GAP
        if items:
            block, bottom = text_block(
                items_text(items, bullet=self.item_bullet),
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
                left=lay.pad + inset,
                width=lay.w - lay.pad * 2 - inset,
            )
            objs.append(block)
            next_top = bottom + GAP
        elif body:
            block, bottom = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
                left=lay.pad + inset,
                width=lay.w - lay.pad * 2 - inset,
            )
            objs.append(block)
            next_top = bottom + GAP
        if callout:
            call_objs, _ = callout_block(
                callout,
                top=next_top,
                lay=lay,
                palette=palette,
                left=lay.pad + inset,
                width=lay.w - lay.pad * 2 - inset,
            )
            objs.extend(call_objs)
        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class ComparisonTemplate(DefaultTemplate):
    """Comparison: two-column A / B split for items."""

    skill_id: ClassVar[str | None] = "comparison"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.3, "gridMode": "none", "photoRatio": 0.44}

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

        heading = clip(s.heading, 120)
        body = clip(s.body, 160) if s.body else ""
        items = list(s.items or [])
        mid = max(1, (len(items) + 1) // 2) if items else 0
        left_items = items[:mid]
        right_items = items[mid:]

        col_w = (lay.w - lay.pad * 2 - 40) / 2
        head_h = text_h(heading, self.head_size, lay.w - lay.pad * 2)
        left_h = text_h(items_text(left_items, bullet="•") or "—", self.body_size, col_w) if items else 0
        right_h = text_h(items_text(right_items, bullet="•") or "—", self.body_size, col_w) if items else 0
        body_h = (GAP + text_h(body, self.body_size, lay.w - lay.pad * 2)) if body and not items else 0
        cols_h = max(left_h, right_h) + 40 if items else 0
        total_h = head_h + GAP + cols_h + body_h
        y = content_start_y(total_h, lay)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_size,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)
        next_top = bottom + GAP

        if items:
            # Column labels
            objs.append(
                textbox(
                    "A",
                    left=lay.pad,
                    top=next_top,
                    width=col_w,
                    font_size=SIZE_META,
                    font_family=FONT,
                    fill=palette.muted,
                    font_weight="700",
                    swibp_style="body",
                )
            )
            objs.append(
                textbox(
                    "B",
                    left=lay.pad + col_w + 40,
                    top=next_top,
                    width=col_w,
                    font_size=SIZE_META,
                    font_family=FONT,
                    fill=palette.accent,
                    font_weight="700",
                    swibp_style="body",
                    swibp_slot="accent",
                )
            )
            next_top += SIZE_META + 12
            # Divider
            objs.append(
                rect(
                    left=lay.w / 2 - 0.75,
                    top=next_top,
                    width=1.5,
                    height=max(left_h, right_h, 80),
                    fill=palette.grid,
                    swibp_slot="accent",
                )
            )
            left_block, _ = text_block(
                items_text(left_items, bullet="•") or "—",
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
                left=lay.pad,
                width=col_w,
            )
            right_block, _ = text_block(
                items_text(right_items, bullet="•") or "—",
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
                left=lay.pad + col_w + 40,
                width=col_w,
            )
            objs.extend([left_block, right_block])
        elif body:
            block, _ = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class ChecklistTemplate(DefaultTemplate):
    """Checklist: checkbox bullets, denser list stack."""

    skill_id: ClassVar[str | None] = "checklist"
    item_bullet: ClassVar[str] = "☐"
    head_size: ClassVar[int] = 46

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.2, "gridMode": "edges", "photoRatio": 0.4}

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

        heading = clip(s.heading, 120)
        body = clip(s.body, 120) if s.body else ""
        items = s.items or ([body] if body else [])
        callout = clip(s.callout, 100) if s.callout else ""
        # Prefer items as checklist rows
        total_h = stack_height(
            heading, "", items, callout, lay, bullet=self.item_bullet, head_size=self.head_size, body_size=28
        )
        y = content_start_y(total_h, lay)
        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=self.head_size,
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
                font_size=28,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)
            next_top = bottom + GAP
        if callout:
            call_objs, _ = callout_block(callout, top=next_top, lay=lay, palette=palette, label="DONE WHEN")
            objs.extend(call_objs)
        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class MythsTemplate(DefaultTemplate):
    """Myths: MYTH tag + TRUTH accent callout."""

    skill_id: ClassVar[str | None] = "myths"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.4, "gridMode": "none", "photoRatio": 0.42}

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
        body = clip(s.body, 180) if s.body else ""
        # heading = myth; callout (or body) = truth
        truth = clip(s.callout or body, 160) if (s.callout or body) else ""
        total_h = (
            SIZE_META
            + 12
            + text_h(heading, self.head_size, lay.w - lay.pad * 2)
            + (GAP + text_h(truth, SIZE_BODY, lay.w - lay.pad * 2 - 32) + 48 if truth else 0)
        )
        y = content_start_y(total_h, lay)

        objs.append(
            textbox(
                "MYTH",
                left=lay.pad,
                top=y,
                width=200,
                font_size=SIZE_META,
                font_family=FONT,
                fill=palette.muted,
                font_weight="700",
                text_align="left",
                line_height=LINE_HEIGHT,
                swibp_style="body",
            )
        )
        head, bottom = text_block(
            heading,
            top=y + SIZE_META + 12,
            lay=lay,
            font_size=self.head_size,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)
        if truth:
            call_objs, _ = callout_block(truth, top=bottom + GAP, lay=lay, palette=palette, label="TRUTH")
            objs.extend(call_objs)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.accent))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class FrameworkTemplate(DefaultTemplate):
    """Framework: numbered stage puck + stacked stages."""

    skill_id: ClassVar[str | None] = "framework"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.25, "gridMode": "none", "photoRatio": 0.4}

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

        stage = max(1, index)
        heading = clip(s.heading, 120)
        body = clip(s.body, 200) if s.body else ""
        items = s.items or []
        puck = 64
        total_h = stack_height(heading, body, items, "", lay, head_size=48, body_size=self.body_size) + 8
        y = content_start_y(total_h, lay)

        objs.append(
            rect(
                left=lay.pad,
                top=y,
                width=puck,
                height=puck,
                fill=palette.accent,
                rx=8,
                ry=8,
                swibp_slot="accent",
            )
        )
        objs.append(
            textbox(
                str(stage),
                left=lay.pad,
                top=y + 14,
                width=puck,
                font_size=32,
                font_family=FONT,
                fill=palette.accent_text,
                font_weight="700",
                text_align="center",
                line_height=LINE_HEIGHT,
                swibp_style="heading",
                swibp_slot="accent",
            )
        )
        head, bottom = text_block(
            heading,
            top=y + 8,
            lay=lay,
            font_size=48,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
            left=lay.pad + puck + 20,
            width=lay.w - lay.pad * 2 - puck - 20,
        )
        objs.append(head)
        next_top = max(bottom, y + puck) + GAP
        if items:
            block, _ = text_block(
                items_text(items, bullet=self.item_bullet),
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)
        elif body:
            block, _ = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.text))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


class PricingTemplate(DefaultTemplate):
    """Pricing: tier callout card as the visual anchor."""

    skill_id: ClassVar[str | None] = "pricing"

    def design_defaults(self) -> dict[str, Any]:
        return {**super().design_defaults(), "accentBias": 0.35, "gridMode": "cover_only", "photoRatio": 0.38}

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

        heading = clip(s.heading, 100)
        body = clip(s.body, 160) if s.body else ""
        items = s.items or []
        callout = clip(s.callout, 80) if s.callout else ""
        price = callout or (items[0] if items else "")
        rest = items[1:] if callout and items else (items[1:] if items and not callout else items)

        price_block_h = (text_h(price, 42, lay.w - lay.pad * 2 - 48) + 56) if price else 0
        total_h = (
            text_h(heading, 44, lay.w - lay.pad * 2)
            + (GAP + price_block_h if price else 0)
            + (GAP + text_h(items_text(rest, bullet=self.item_bullet), self.body_size, lay.w - lay.pad * 2) if rest else 0)
            + (GAP + text_h(body, self.body_size, lay.w - lay.pad * 2) if body and not rest else 0)
        )
        y = content_start_y(total_h, lay)

        head, bottom = text_block(
            heading,
            top=y,
            lay=lay,
            font_size=44,
            font_weight="bold",
            fill=palette.text,
            swibp_style="heading",
        )
        objs.append(head)
        next_top = bottom + GAP
        if price:
            call_objs, next_top = callout_block(price, top=next_top, lay=lay, palette=palette, label="TIER")
            # Enlarge price feel: bump first text after label
            objs.extend(call_objs)
            next_top += GAP
        if rest:
            block, _ = text_block(
                items_text(rest, bullet=self.item_bullet),
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)
        elif body:
            block, _ = text_block(
                body,
                top=next_top,
                lay=lay,
                font_size=self.body_size,
                font_weight="500",
                fill=palette.text,
                swibp_style="body",
            )
            objs.append(block)

        objs.extend(footer(lay, category, fill_cat=palette.muted, fill_arrow=palette.accent))
        return slide(palette.bg, objs, width=lay.w, height=lay.h)


# All skill template classes (for registry import)
SKILL_TEMPLATE_CLASSES: list[type[DefaultTemplate]] = [
    LaunchTemplate,
    HowtoTemplate,
    OfferTemplate,
    TipsTemplate,
    StoryTemplate,
    ComparisonTemplate,
    ChecklistTemplate,
    MythsTemplate,
    FrameworkTemplate,
    PricingTemplate,
]
