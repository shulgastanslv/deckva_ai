"""LLM generate for aesthetic CORA branch."""

from __future__ import annotations

from typing import Any

from app.cora.aesthetic.prompts import AESTHETIC_SYSTEM, aesthetic_user
from app.llm import chat_json
from app.schemas import SlideContent

_VALID_KINDS = {
    "photo",
    "scrim",
    "heading",
    "body",
    "pill",
    "handle",
    "footer",
    "counter",
    "callout",
}
_VALID_ALIGN = {"left", "center", "right"}
_VALID_CASE = {"lower", "upper", "as_is"}
_VALID_SIZE = {"hero", "display", "body", "meta"}
_VALID_ICON = {"pin", "bookmark", "send", "none", ""}
_VALID_STYLE = {"plain", "pill", ""}


def _clamp01(value: Any, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, v))


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [p.strip() for p in value.replace("|", "\n").split("\n") if p.strip()]
    return []


def _normalize_element(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in _VALID_KINDS:
        return None
    el: dict[str, Any] = {
        "kind": kind,
        "x": _clamp01(raw.get("x"), 0.0),
        "y": _clamp01(raw.get("y"), 0.0),
        "w": _clamp01(raw.get("w"), 1.0 if kind in {"photo", "scrim", "heading", "body"} else 0.35),
        "h": _clamp01(raw.get("h"), 1.0 if kind in {"photo", "scrim"} else 0.12),
    }
    if el["w"] < 0.04:
        el["w"] = 0.2
    if el["h"] < 0.02 and kind in {"photo", "scrim"}:
        el["h"] = 0.2
    if kind == "photo":
        try:
            el["slot"] = max(0, int(raw.get("slot", 0)))
        except (TypeError, ValueError):
            el["slot"] = 0
    if kind == "scrim":
        try:
            opacity = float(raw.get("opacity", 0.22))
        except (TypeError, ValueError):
            opacity = 0.22
        el["opacity"] = max(0.05, min(0.55, opacity))
        color = str(raw.get("color") or "#000000").strip()
        el["color"] = color if color.startswith("#") and len(color) == 7 else "#000000"
    if kind in {"heading", "body", "pill", "handle", "footer", "counter", "callout"}:
        align = str(raw.get("align") or "left").strip().lower()
        el["align"] = align if align in _VALID_ALIGN else "left"
        case = str(raw.get("case") or "as_is").strip().lower()
        el["case"] = case if case in _VALID_CASE else "as_is"
        size = str(raw.get("size") or ("hero" if kind == "heading" else "body")).strip().lower()
        el["size"] = size if size in _VALID_SIZE else "body"
        color = str(raw.get("color") or "").strip()
        el["color"] = color if color.startswith("#") and len(color) in {7, 4} else ""
        el["stack"] = bool(raw.get("stack")) if kind == "heading" else False
        el["text"] = str(raw.get("text") or "").strip()
        icon = str(raw.get("icon") or "none").strip().lower()
        el["icon"] = icon if icon in _VALID_ICON else "none"
        style = str(raw.get("style") or ("pill" if kind == "pill" else "plain")).strip().lower()
        el["style"] = style if style in _VALID_STYLE else "plain"
        try:
            opacity = float(raw.get("opacity", 1.0))
        except (TypeError, ValueError):
            opacity = 1.0
        el["opacity"] = max(0.35, min(1.0, opacity))
    return el


def _default_cover_elements() -> list[dict[str, Any]]:
    return [
        {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 1, "slot": 0},
        {"kind": "scrim", "x": 0, "y": 0, "w": 1, "h": 1, "opacity": 0.22, "color": "#000000"},
        {
            "kind": "heading",
            "x": 0.07,
            "y": 0.12,
            "w": 0.86,
            "h": 0.45,
            "align": "left",
            "case": "lower",
            "size": "hero",
            "stack": True,
            "color": "#F2E6A8",
            "text": "",
            "icon": "none",
            "style": "plain",
            "opacity": 1.0,
        },
        {
            "kind": "body",
            "x": 0.07,
            "y": 0.72,
            "w": 0.7,
            "h": 0.12,
            "align": "left",
            "case": "lower",
            "size": "body",
            "stack": False,
            "color": "#FFFFFF",
            "text": "",
            "icon": "none",
            "style": "plain",
            "opacity": 0.92,
        },
        {
            "kind": "handle",
            "x": 0.07,
            "y": 0.04,
            "w": 0.4,
            "h": 0.05,
            "align": "left",
            "case": "as_is",
            "size": "meta",
            "stack": False,
            "color": "#FFFFFF",
            "text": "",
            "icon": "none",
            "style": "plain",
            "opacity": 0.9,
        },
    ]


def _default_mid_elements(index: int) -> list[dict[str, Any]]:
    return [
        {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 0.5, "slot": 0},
        {"kind": "photo", "x": 0, "y": 0.5, "w": 1, "h": 0.5, "slot": 1},
        {
            "kind": "scrim",
            "x": 0,
            "y": 0,
            "w": 1,
            "h": 0.5,
            "opacity": 0.18,
            "color": "#000000",
        },
        {
            "kind": "scrim",
            "x": 0,
            "y": 0.5,
            "w": 1,
            "h": 0.5,
            "opacity": 0.18,
            "color": "#000000",
        },
        {
            "kind": "counter",
            "x": 0.07,
            "y": 0.08,
            "w": 0.2,
            "h": 0.05,
            "align": "left",
            "case": "as_is",
            "size": "meta",
            "text": f"[{index}]",
            "color": "#FFFFFF",
            "icon": "none",
            "style": "plain",
            "stack": False,
            "opacity": 1.0,
        },
        {
            "kind": "heading",
            "x": 0.07,
            "y": 0.14,
            "w": 0.8,
            "h": 0.25,
            "align": "left",
            "case": "as_is",
            "size": "display",
            "stack": False,
            "color": "#FFFFFF",
            "text": "",
            "icon": "none",
            "style": "plain",
            "opacity": 1.0,
        },
        {
            "kind": "handle",
            "x": 0.32,
            "y": 0.47,
            "w": 0.36,
            "h": 0.06,
            "align": "center",
            "case": "as_is",
            "size": "meta",
            "stack": False,
            "color": "#1A1A1A",
            "text": "",
            "icon": "none",
            "style": "pill",
            "opacity": 1.0,
        },
    ]


def _default_cta_elements() -> list[dict[str, Any]]:
    return [
        {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 1, "slot": 0},
        {"kind": "scrim", "x": 0, "y": 0, "w": 1, "h": 1, "opacity": 0.28, "color": "#000000"},
        {
            "kind": "heading",
            "x": 0.08,
            "y": 0.38,
            "w": 0.84,
            "h": 0.22,
            "align": "center",
            "case": "lower",
            "size": "display",
            "stack": False,
            "color": "#F2E6A8",
            "text": "",
            "icon": "none",
            "style": "plain",
            "opacity": 1.0,
        },
        {
            "kind": "body",
            "x": 0.12,
            "y": 0.62,
            "w": 0.76,
            "h": 0.12,
            "align": "center",
            "case": "as_is",
            "size": "body",
            "stack": False,
            "color": "#FFFFFF",
            "text": "",
            "icon": "none",
            "style": "plain",
            "opacity": 0.92,
        },
    ]


def normalize_aesthetic_slide(
    raw: Any,
    *,
    index: int,
    slides_count: int,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RuntimeError(f"Aesthetic slide #{index + 1}: ожидался объект.")
    heading = str(raw.get("heading") or "").strip()
    if not heading:
        raise RuntimeError(f"Aesthetic slide #{index + 1}: пустой heading.")

    elements_raw = raw.get("elements")
    elements: list[dict[str, Any]] = []
    if isinstance(elements_raw, list):
        for item in elements_raw:
            el = _normalize_element(item)
            if el:
                elements.append(el)

    is_last = index == slides_count - 1
    is_first = index == 0
    if not elements:
        if is_first:
            elements = _default_cover_elements()
        elif is_last:
            elements = _default_cta_elements()
        else:
            elements = _default_mid_elements(index)

    # Ensure at least one photo region on non-empty prompt slides / cover
    if not any(e["kind"] == "photo" for e in elements) and not is_last:
        elements.insert(0, {"kind": "photo", "x": 0, "y": 0, "w": 1, "h": 1, "slot": 0})

    prompts = _as_list(raw.get("image_prompts"))
    if not prompts:
        single = str(raw.get("image_prompt") or "").strip()
        if single:
            prompts = [single]
    max_slot = max((int(e.get("slot", 0)) for e in elements if e["kind"] == "photo"), default=-1)
    while len(prompts) <= max_slot:
        prompts.append(prompts[-1] if prompts else "editorial lifestyle aesthetic photo")

    return {
        "heading": heading,
        "body": str(raw.get("body") or "").strip(),
        "badges": _as_list(raw.get("badges")),
        "callout": str(raw.get("callout") or "").strip(),
        "footer": str(raw.get("footer") or "").strip(),
        "image_prompts": prompts,
        "elements": elements,
        "role": "cover" if is_first else ("cta" if is_last else "mid"),
    }


def parse_aesthetic_raw(raw: dict[str, Any], slides_count: int) -> dict[str, Any]:
    title = str(raw.get("title") or "").strip()
    if not title:
        raise RuntimeError("Aesthetic: ИИ не вернул title.")
    category = str(raw.get("category") or "").strip().split()[0] if raw.get("category") else ""
    if not category:
        raise RuntimeError("Aesthetic: ИИ не вернул category.")

    slides_raw = raw.get("slides")
    if not isinstance(slides_raw, list) or not slides_raw:
        raise RuntimeError("Aesthetic: ИИ не вернул slides.")

    slides: list[dict[str, Any]] = []
    for i, item in enumerate(slides_raw):
        slides.append(normalize_aesthetic_slide(item, index=i, slides_count=slides_count))
        if len(slides) >= slides_count:
            break
    if len(slides) < slides_count:
        raise RuntimeError(f"Aesthetic: ИИ вернул {len(slides)} из {slides_count} слайдов.")

    return {
        "title": title,
        "tagline": str(raw.get("tagline") or "").strip(),
        "category": category,
        "moodHint": str(raw.get("moodHint") or raw.get("mood_hint") or "pinterest editorial warm").strip(),
        "slides": slides[:slides_count],
    }


def to_slide_contents(aesthetic: dict[str, Any]) -> list[SlideContent]:
    """Bridge to existing SlideContent for plan binding / stock helpers."""
    out: list[SlideContent] = []
    slides = aesthetic.get("slides") or []
    n = len(slides)
    for i, s in enumerate(slides):
        layout = "cover" if i == 0 else ("cta" if i == n - 1 else "statement")
        prompts = s.get("image_prompts") or []
        out.append(
            SlideContent(
                layout=layout,  # type: ignore[arg-type]
                heading=str(s.get("heading") or ""),
                body=str(s.get("body") or ""),
                badges=list(s.get("badges") or []),
                callout=str(s.get("callout") or ""),
                tag=str(s.get("footer") or ""),
                image_prompt=str(prompts[0] if prompts else ""),
                items=list(prompts[1:] if len(prompts) > 1 else []),
            )
        )
    return out


async def generate_aesthetic_carousel(
    *,
    topic: str,
    slides_count: int,
    language: str,
    handle: str,
    model_id: str,
    seed_text: str = "",
) -> dict[str, Any]:
    if not topic.strip():
        raise RuntimeError("Не указан topic.")
    raw = await chat_json(
        system=AESTHETIC_SYSTEM,
        user=aesthetic_user(
            topic=topic,
            language=language,
            slides_count=slides_count,
            handle=handle,
            seed_text=seed_text,
        ),
        temperature=1.0,
        max_tokens=4500,
        model_id=model_id,
    )
    return parse_aesthetic_raw(raw, slides_count)
