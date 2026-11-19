"""Assemble Fabric slides from LLM-invented aesthetic element layouts."""

from __future__ import annotations

import time
from typing import Any

from app.cora.assemble import palette_response, stamp_cora_object_ids
from app.fabric import canvas_size, image, normalize_aspect, rect, slide, textbox
from app.fonts import Typography, current_font, push_typography, reset_typography
from app.palette import Palette
from app.templates.base import clip, handle_text, text_h

_ICON = {
    "pin": "⌖ ",
    "bookmark": "ﾉ ",
    "send": "✈ ",
    "none": "",
    "": "",
}

def _font_size(size_key: str, typography: Typography) -> int:
    key = (size_key or "body").lower()
    if key == "hero":
        return max(typography.head_size, min(70, typography.head_size + 8))
    if key == "display":
        return min(70, max(32, typography.head_size))
    if key == "meta":
        return max(12, min(24, typography.meta_size))
    return max(16, min(36, typography.body_size))


def _apply_case(text: str, case: str) -> str:
    if case == "lower":
        return text.lower()
    if case == "upper":
        return text.upper()
    return text


def _stack_words(text: str, *, max_lines: int = 7) -> str:
    words = [w for w in (text or "").split() if w]
    if not words:
        return ""
    if len(words) <= max_lines:
        return "\n".join(words)
    # pack roughly evenly into max_lines
    out: list[str] = []
    i = 0
    n = max_lines
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
    return "\n".join(out)


def _resolve_text(
    el: dict[str, Any],
    *,
    slide_data: dict[str, Any],
    handle: str,
    index: int,
    slides_count: int,
) -> str:
    kind = el["kind"]
    explicit = str(el.get("text") or "").strip()
    if explicit:
        base = explicit
    elif kind == "heading":
        base = str(slide_data.get("heading") or "")
    elif kind == "body":
        base = str(slide_data.get("body") or "")
    elif kind == "callout":
        base = str(slide_data.get("callout") or "")
    elif kind == "footer":
        base = str(slide_data.get("footer") or "")
    elif kind == "handle":
        base = handle
    elif kind == "counter":
        base = f"{index + 1}/{slides_count}"
    elif kind == "pill":
        badges = slide_data.get("badges") or []
        base = str(badges[0]) if badges else ""
    else:
        base = ""
    base = clip(base, 220)
    if kind == "heading" and el.get("stack"):
        base = _stack_words(_apply_case(base, el.get("case") or "as_is"))
        return base
    if kind == "callout" and base and not (base.startswith("[") and base.endswith("]")):
        base = f"[{base}]"
    if kind == "pill":
        icon = _ICON.get(str(el.get("icon") or "none"), "")
        return f"{icon}{_apply_case(base, el.get('case') or 'upper')}".strip()
    return _apply_case(base, el.get("case") or "as_is")


def _pill_box(
    text: str,
    *,
    left: float,
    top: float,
    font_size: int,
    font_family: str,
    fill: str,
    canvas_w: float,
) -> list[dict[str, Any]]:
    pad_x = 18
    pad_y = 10
    approx_w = min(canvas_w * 0.55, max(90.0, len(text) * font_size * 0.52 + pad_x * 2))
    h = font_size * 1.35 + pad_y
    bg = rect(
        left=left,
        top=top,
        width=approx_w,
        height=h,
        fill="#2A2A2A",
        rx=h / 2,
        ry=h / 2,
        opacity=0.45,
        swibp_slot="accent",
    )
    tx = textbox(
        text,
        left=left + pad_x * 0.55,
        top=top + pad_y * 0.45,
        width=approx_w - pad_x,
        font_size=font_size,
        font_family=font_family,
        fill=fill or "#FFFFFF",
        font_weight="500",
        text_align="left",
        line_height=1.05,
        swibp_style="body",
        opacity=0.95,
    )
    return [bg, tx]


def render_aesthetic_slide(
    slide_data: dict[str, Any],
    *,
    index: int,
    slides_count: int,
    width: int,
    height: int,
    handle: str,
    palette: Palette,
    typography: Typography,
    photos: list[str],
) -> dict[str, Any]:
    objs: list[dict[str, Any]] = []
    font = typography.font_family or current_font()
    elements = list(slide_data.get("elements") or [])
    # photos first, then scrims, then text (stable paint order)
    order = {"photo": 0, "scrim": 1, "heading": 2, "body": 3, "callout": 4, "pill": 5, "counter": 6, "footer": 7, "handle": 8}
    elements = sorted(elements, key=lambda e: order.get(e.get("kind", ""), 9))

    pill_badge_i = 0
    badges = list(slide_data.get("badges") or [])

    for el in elements:
        kind = el["kind"]
        x = float(el["x"]) * width
        y = float(el["y"]) * height
        w = max(8.0, float(el["w"]) * width)
        h = max(8.0, float(el["h"]) * height)

        if kind == "photo":
            slot = int(el.get("slot") or 0)
            src = ""
            if 0 <= slot < len(photos):
                src = (photos[slot] or "").strip()
            if src:
                objs.append(image(src, left=x, top=y, width=w, height=h, swibp_slot="image"))
            else:
                objs.append(
                    rect(
                        left=x,
                        top=y,
                        width=w,
                        height=h,
                        fill=palette.photo,
                        swibp_slot="image",
                    )
                )
            continue

        if kind == "scrim":
            objs.append(
                rect(
                    left=x,
                    top=y,
                    width=w,
                    height=h,
                    fill=str(el.get("color") or "#000000"),
                    opacity=float(el.get("opacity") or 0.22),
                    swibp_slot="accent",
                )
            )
            continue

        if kind == "handle" and not (handle or "").strip():
            continue

        # For successive pills without explicit text, consume badges in order
        if kind == "pill" and not str(el.get("text") or "").strip() and pill_badge_i < len(badges):
            el = {**el, "text": badges[pill_badge_i]}
            pill_badge_i += 1

        text = _resolve_text(
            el,
            slide_data=slide_data,
            handle=handle,
            index=index,
            slides_count=slides_count,
        )
        if not text:
            continue

        size = _font_size(str(el.get("size") or "body"), typography)
        color = str(el.get("color") or "").strip() or (
            "#F2E6A8" if kind in {"heading", "callout"} else "#FFFFFF"
        )
        align = str(el.get("align") or "left")
        opacity = float(el.get("opacity") or 1.0)
        style = str(el.get("style") or "plain")
        swibp = "heading" if kind == "heading" else "body"
        role = "handle" if kind == "handle" else ("counter" if kind == "counter" else None)

        if kind in {"pill", "handle"} and style == "pill":
            objs.extend(
                _pill_box(
                    text,
                    left=x,
                    top=y,
                    font_size=size,
                    font_family=font,
                    fill=color,
                    canvas_w=width,
                )
            )
            if role:
                # mark last textbox
                for o in reversed(objs):
                    if o.get("type") == "Textbox":
                        o["swibpRole"] = role
                        break
            continue

        # Cap text box height loosely from element h when stack/multi-line
        line_h = 0.92 if el.get("stack") else 1.05
        estimated = text_h(text, size, w)
        box_h = max(estimated, min(h, estimated * 1.15)) if kind == "heading" else None
        objs.append(
            textbox(
                text,
                left=x,
                top=y,
                width=w,
                font_size=size,
                font_family=font,
                fill=color,
                font_weight="700" if kind == "heading" else "500",
                text_align=align,
                line_height=line_h,
                swibp_style=swibp,
                swibp_role=role,
                height=box_h,
                opacity=opacity,
            )
        )

    bg = palette.bg
    # Prefer near-black matte behind photo carousels
    if any(e.get("kind") == "photo" for e in elements):
        bg = "#111111"
    return slide(bg, objs, width=width, height=height)


def assemble_aesthetic_carousel(
    *,
    aesthetic: dict[str, Any],
    ratio: str,
    palette: Palette,
    plan: dict[str, Any],
    cora_run_id: str,
    save: bool,
    slide_photo_sets: list[list[str]],
    typography: Typography,
    handle: str,
    show_handle: bool,
) -> dict[str, Any]:
    from pathlib import Path
    import json
    from app.cora.assemble import slug

    aspect = normalize_aspect(ratio)
    width, height = canvas_size(aspect)
    slides_data = list(aesthetic.get("slides") or [])
    n = len(slides_data)
    if n < 1:
        raise RuntimeError("Aesthetic: нет слайдов для сборки.")

    token = push_typography(typography)
    try:
        if show_handle:
            handle_resolved = handle_text(handle)
        else:
            handle_resolved = ""

        fabric_slides = []
        for i, s in enumerate(slides_data):
            photos = slide_photo_sets[i] if i < len(slide_photo_sets) else []
            fabric_slides.append(
                render_aesthetic_slide(
                    s,
                    index=i,
                    slides_count=n,
                    width=width,
                    height=height,
                    handle=handle_resolved,
                    palette=palette,
                    typography=typography,
                    photos=photos,
                )
            )
    finally:
        reset_typography(token)

    design = plan.get("design") if isinstance(plan.get("design"), dict) else {}
    design = {
        **design,
        "engine": "aesthetic_llm",
        "templateId": "aesthetic_llm",
        "typography": typography.to_dict(),
        "fontFamily": typography.font_family,
        "showHandle": show_handle,
        "moodHint": aesthetic.get("moodHint") or design.get("mood"),
    }
    plan["design"] = design

    carousel = {
        "title": aesthetic["title"],
        "aspectRatio": aspect,
        "width": width,
        "height": height,
        "design": design,
        "typography": typography.to_dict(),
        "templateId": "aesthetic_llm",
        "slides": fabric_slides,
    }
    carousel = stamp_cora_object_ids(carousel, plan)

    path: str | None = None
    if save:
        out_dir = Path(__file__).resolve().parent.parent.parent.parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_{slug(aesthetic['title'])}.json"
        public = {
            "coraRunId": cora_run_id,
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "palette": palette.to_dict(),
            "typography": carousel.get("typography"),
            "plan": plan,
            "aesthetic": aesthetic,
            "slides": carousel["slides"],
        }
        out.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
        path = str(out)

    return {
        "title": aesthetic["title"],
        "aspectRatio": aspect,
        "width": width,
        "height": height,
        "path": path,
        "palette": palette_response(palette),
        "typography": carousel.get("typography"),
        "carousel": {
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "typography": carousel.get("typography"),
            "templateId": "aesthetic_llm",
            "slides": carousel["slides"],
        },
    }
