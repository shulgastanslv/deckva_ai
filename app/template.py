"""Шаблоны карусели: left-align, блок по центру вертикали, счётчик ( n )."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any

from app.fabric import canvas_size, normalize_aspect, rect, slide, textbox
from app.schemas import CarouselContent, SlideContent

BG = "#ffffff"
GRID = "#cfcfcf"
PHOTO = "#c8c8c8"
TEXT = "#111111"
MUTED = "#9a9a9a"
ON_ACCENT = "#2a2a2a"  # тёмный текст на пастели читается лучше белого
FONT = "Montserrat"

SIZE_HEAD = 55
SIZE_BODY = 25
SIZE_META = 20
GAP = 10  # всегда 10px после заголовка / между текстовыми блоками
LINE_HEIGHT = 0.90
GRID_OPACITY = 0.22
PHOTO_TEXT_GAP = 20  # отступ текста от картинки на 1-м слайде

PASTELS = [
    "#F6C1C0",  # rose
    "#F7D9A8",  # peach
    "#F3E5AB",  # butter
    "#C9E4CA",  # mint
    "#B8D4E8",  # sky
    "#D7C6E6",  # lilac
    "#F5C6D0",  # pink
    "#C5E0DC",  # aqua
    "#E8D5B7",  # sand
    "#D4E6F1",  # powder blue
    "#EAD7F5",  # soft violet
    "#FFE0B2",  # soft apricot
]


@dataclass
class L:
    w: int
    h: int
    pad: float
    step: float


def _L(w: int, h: int) -> L:
    base = min(w, h)
    return L(w=w, h=h, pad=max(48, base * 0.06), step=max(72, base * 0.085))


def _handle(h: str) -> str:
    h = h.strip()
    if not h:
        raise RuntimeError("Не указан handle.")
    return h if h.startswith("@") else f"@{h}"


def _clip(t: str, n: int) -> str:
    t = (t or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _line_count(text: str, font_size: int, width: float) -> int:
    """Консервативный подсчёт строк (жирный кириллический sans)."""
    avg = font_size * 0.62  # шире, чтобы не недооценить перенос
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


def _text_h(text: str, font_size: int, width: float) -> float:
    """Высота текстового блока. При lineHeight < 1 всё равно резервируем место под глифы."""
    lines = _line_count(text, font_size, width)
    # высота строки ≈ fontSize (глиф), lineHeight только визуальный шаг в Fabric
    return lines * font_size * max(LINE_HEIGHT, 0.95) + 4


def _grid(w: int, h: int, step: float, *, top: float = 0, height: float | None = None) -> list[dict[str, Any]]:
    hh = height if height is not None else h - top
    objs: list[dict[str, Any]] = []
    x = 0.0
    while x <= w + 0.5:
        objs.append(rect(left=x, top=top, width=1.2, height=hh, fill=GRID, opacity=GRID_OPACITY, swibp_slot="accent"))
        x += step
    y = top
    while y <= top + hh + 0.5:
        objs.append(rect(left=0, top=y, width=w, height=1.2, fill=GRID, opacity=GRID_OPACITY, swibp_slot="accent"))
        y += step
    return objs


def _counter(index: int, lay: L, *, fill: str = TEXT) -> dict[str, Any]:
    """Счётчик всегда в круглых скобках: ( 1 )"""
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


def _footer(lay: L, category: str, *, fill_cat: str = MUTED, fill_arrow: str = TEXT) -> list[dict[str, Any]]:
    return [
        textbox(
            _clip(category, 24),
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


def _text_block(
    text: str,
    *,
    top: float,
    lay: L,
    font_size: int,
    font_weight: str | int = "bold",
    fill: str = TEXT,
    swibp_style: str = "heading",
) -> tuple[dict[str, Any], float]:
    """
    Один Textbox left-align.
    Возвращает (obj, bottom_y) — bottom_y = top + height, без gap.
    Следующий блок ставить на bottom_y + GAP.
    """
    width = lay.w - lay.pad * 2
    h = _text_h(text, font_size, width)
    obj = textbox(
        text,
        left=lay.pad,
        top=top,
        width=width,
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


def _items_text(items: list[str]) -> str:
    lines = []
    for raw in items:
        t = re.sub(r"^[\s→\-\d\.]+", "", (raw or "").strip())
        if t:
            lines.append(f"→ {t}")
    return "\n".join(lines)


def _stack_height(heading: str, body: str, items: list[str], callout: str, lay: L) -> float:
    width = lay.w - lay.pad * 2
    h = _text_h(heading, SIZE_HEAD, width)
    if items:
        h += GAP + _text_h(_items_text(items), SIZE_BODY, width)
    elif body:
        h += GAP + _text_h(body, SIZE_BODY, width)
    if callout:
        h += GAP + _text_h(callout, SIZE_BODY, width - 32) + 28
    return h


def _content_start_y(total_h: float, lay: L, *, zone_top: float = 0, zone_bottom: float | None = None) -> float:
    bottom = zone_bottom if zone_bottom is not None else lay.h
    y = zone_top + (bottom - zone_top - total_h) / 2
    min_y = zone_top + (PHOTO_TEXT_GAP if zone_top > 0 else lay.pad * 1.8)
    max_y = bottom - total_h - lay.pad * 2.2
    return max(min_y, min(y, max_y))


def _pastel(rng: random.Random) -> str:
    return rng.choice(PASTELS)


def _callout_block(text: str, *, top: float, lay: L, fill: str) -> tuple[list[dict[str, Any]], float]:
    width = lay.w - lay.pad * 2
    pad_y = 14
    th = _text_h(text, SIZE_BODY, width - 32) + pad_y * 2
    objs = [
        rect(left=lay.pad, top=top, width=width, height=th, fill=fill, rx=0, ry=0, swibp_slot="accent"),
        textbox(
            text,
            left=lay.pad + 16,
            top=top + pad_y,
            width=width - 32,
            height=th - pad_y * 2,
            font_size=SIZE_BODY,
            font_family=FONT,
            fill=ON_ACCENT,
            font_weight="700",
            text_align="left",
            line_height=LINE_HEIGHT,
            swibp_style="heading",
            swibp_slot="accent",
        ),
    ]
    return objs, top + th


# -------------------- layouts --------------------


def layout_cover(
    s: SlideContent,
    lay: L,
    handle: str,
    category: str,
    *,
    index: int,
    with_grid: bool,
    rng: random.Random,
) -> dict[str, Any]:
    photo_h = lay.h * 0.48
    objs: list[dict[str, Any]] = [
        rect(left=0, top=0, width=lay.w, height=photo_h, fill=PHOTO, swibp_slot="image"),
        rect(left=0, top=photo_h, width=lay.w, height=lay.h - photo_h, fill=BG, swibp_slot="card"),
    ]
    if with_grid:
        objs.extend(_grid(lay.w, lay.h, lay.step, top=photo_h, height=lay.h - photo_h))

    objs.append(
        textbox(
            handle,
            left=lay.pad,
            top=lay.pad * 0.7,
            width=lay.w * 0.45,
            font_size=SIZE_META,
            font_family=FONT,
            fill="#ffffff",
            font_weight="600",
            text_align="left",
            line_height=LINE_HEIGHT,
            swibp_style="body",
            swibp_role="handle",
        )
    )
    objs.append(_counter(index, lay, fill="#ffffff"))

    heading = _clip(s.heading, 120)
    body = _clip(s.body, 200) if s.body else ""
    total_h = _stack_height(heading, body, [], "", lay)

    # строго 20px от низа картинки — затем можно чуть опустить при центрировании, но не ближе 20px
    y = _content_start_y(total_h, lay, zone_top=photo_h + PHOTO_TEXT_GAP, zone_bottom=lay.h)
    y = max(y, photo_h + PHOTO_TEXT_GAP)

    head, bottom = _text_block(heading, top=y, lay=lay, font_size=SIZE_HEAD, font_weight="bold", swibp_style="heading")
    objs.append(head)
    if body:
        b, _ = _text_block(body, top=bottom + GAP, lay=lay, font_size=SIZE_BODY, font_weight="500", swibp_style="body")
        objs.append(b)

    objs.extend(_footer(lay, category))
    return slide(BG, objs, width=lay.w, height=lay.h)


def layout_content(
    s: SlideContent,
    lay: L,
    handle: str,
    category: str,
    *,
    index: int,
    with_grid: bool,
    rng: random.Random,
) -> dict[str, Any]:
    objs: list[dict[str, Any]] = [rect(left=0, top=0, width=lay.w, height=lay.h, fill=BG, swibp_slot="card")]
    if with_grid:
        objs.extend(_grid(lay.w, lay.h, lay.step))

    objs.append(
        textbox(
            handle,
            left=lay.pad,
            top=lay.pad * 0.7,
            width=lay.w * 0.45,
            font_size=SIZE_META,
            font_family=FONT,
            fill=TEXT,
            font_weight="500",
            text_align="left",
            line_height=LINE_HEIGHT,
            swibp_style="body",
            swibp_role="handle",
        )
    )
    objs.append(_counter(index, lay))

    heading = _clip(s.heading, 140)
    body = _clip(s.body, 220) if s.body else ""
    items = s.items or []
    callout = _clip(s.callout, 140) if s.callout else ""
    total_h = _stack_height(heading, body, items, callout, lay)
    y = _content_start_y(total_h, lay)

    head, bottom = _text_block(heading, top=y, lay=lay, font_size=SIZE_HEAD, font_weight="bold", swibp_style="heading")
    objs.append(head)

    next_top = bottom + GAP
    if items:
        block, bottom = _text_block(
            _items_text(items),
            top=next_top,
            lay=lay,
            font_size=SIZE_BODY,
            font_weight="500",
            swibp_style="body",
        )
        objs.append(block)
        next_top = bottom + GAP
    elif body:
        block, bottom = _text_block(body, top=next_top, lay=lay, font_size=SIZE_BODY, font_weight="500", swibp_style="body")
        objs.append(block)
        next_top = bottom + GAP

    if callout:
        call_objs, _ = _callout_block(callout, top=next_top, lay=lay, fill=_pastel(rng))
        objs.extend(call_objs)

    objs.extend(_footer(lay, category))
    return slide(BG, objs, width=lay.w, height=lay.h)


def layout_orange_quote(
    s: SlideContent,
    lay: L,
    handle: str,
    category: str,
    *,
    index: int,
    rng: random.Random,
) -> dict[str, Any]:
    bg = _pastel(rng)
    objs: list[dict[str, Any]] = [rect(left=0, top=0, width=lay.w, height=lay.h, fill=bg, swibp_slot="card")]
    objs.append(
        textbox(
            handle,
            left=lay.pad,
            top=lay.pad * 0.7,
            width=lay.w * 0.45,
            font_size=SIZE_META,
            font_family=FONT,
            fill=TEXT,
            font_weight="500",
            line_height=LINE_HEIGHT,
            swibp_role="handle",
            swibp_style="body",
        )
    )
    objs.append(_counter(index, lay, fill=TEXT))

    heading = _clip(s.heading, 180)
    total_h = _stack_height(heading, "", [], "", lay)
    y = _content_start_y(total_h, lay)
    head, _ = _text_block(heading, top=y, lay=lay, font_size=SIZE_HEAD, font_weight="bold", fill=TEXT, swibp_style="heading")
    objs.append(head)
    objs.extend(_footer(lay, category, fill_cat=TEXT, fill_arrow=TEXT))
    return slide(bg, objs, width=lay.w, height=lay.h)


def layout_cta(
    s: SlideContent,
    lay: L,
    handle: str,
    category: str,
    *,
    index: int,
    with_grid: bool,
    rng: random.Random,
) -> dict[str, Any]:
    objs: list[dict[str, Any]] = [rect(left=0, top=0, width=lay.w, height=lay.h, fill=BG, swibp_slot="card")]
    if with_grid:
        objs.extend(_grid(lay.w, lay.h, lay.step))

    objs.append(
        textbox(
            handle,
            left=lay.pad,
            top=lay.pad * 0.7,
            width=lay.w * 0.45,
            font_size=SIZE_META,
            font_family=FONT,
            fill=TEXT,
            font_weight="500",
            line_height=LINE_HEIGHT,
            swibp_role="handle",
            swibp_style="body",
        )
    )
    objs.append(_counter(index, lay))

    heading = _clip(s.callout or s.heading, 140)
    body = _clip(s.body, 160) if s.body else ""
    total_h = _stack_height(heading, body, [], "", lay)
    y = _content_start_y(total_h, lay)

    head, bottom = _text_block(heading, top=y, lay=lay, font_size=SIZE_HEAD, font_weight="bold", swibp_style="heading")
    objs.append(head)
    if body:
        b, _ = _text_block(body, top=bottom + GAP, lay=lay, font_size=SIZE_BODY, font_weight="500", swibp_style="body")
        objs.append(b)

    objs.extend(_footer(lay, category))
    return slide(BG, objs, width=lay.w, height=lay.h)


def build_slide(
    s: SlideContent,
    *,
    index: int,
    total: int,
    lay: L,
    handle: str,
    category: str,
    rng: random.Random,
) -> dict[str, Any]:
    is_first = index == 0
    is_last = index == total - 1
    with_grid = is_first or is_last

    layout = s.layout
    if is_first:
        layout = "cover"
    elif is_last:
        layout = "cta"
    elif layout == "orange_quote" and rng.random() > 0.30:
        layout = "statement"

    if layout == "cover":
        return layout_cover(s, lay, handle, category, index=index, with_grid=with_grid, rng=rng)
    if layout == "orange_quote":
        return layout_orange_quote(s, lay, handle, category, index=index, rng=rng)
    if layout == "cta":
        return layout_cta(s, lay, handle, category, index=index, with_grid=with_grid, rng=rng)
    return layout_content(s, lay, handle, category, index=index, with_grid=False, rng=rng)


def build_carousel(
    content: CarouselContent,
    *,
    aspect_ratio: str,
    seed: int | None = None,
) -> dict[str, Any]:
    aspect = normalize_aspect(aspect_ratio)
    w, h = canvas_size(aspect)
    rng = random.Random(seed)
    lay = _L(w, h)
    handle = _handle(content.handle)
    category = content.category.strip()
    if not category:
        raise RuntimeError("Не указан category.")
    total = len(content.slides)
    if total < 1:
        raise RuntimeError("Нет слайдов для сборки.")

    slides_out = [
        build_slide(s, index=i, total=total, lay=lay, handle=handle, category=category, rng=rng)
        for i, s in enumerate(content.slides)
    ]

    return {
        "title": content.title,
        "aspectRatio": aspect,
        "width": w,
        "height": h,
        "slides": slides_out,
    }
