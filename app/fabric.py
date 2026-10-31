"""Fabric.js / swibp canvas helpers."""

from __future__ import annotations

from typing import Any

FABRIC_VERSION = "6.9.1"

# base width 1080 for portrait; 16:9 uses 1920 width
ASPECT_SIZES: dict[str, tuple[int, int]] = {
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
}


def normalize_aspect(value: str) -> str:
    if not value or not str(value).strip():
        raise ValueError("Не указан aspectRatio.")
    raw = str(value).strip().lower().replace(";", ":").replace("х", ":").replace("x", ":")
    raw = raw.replace(" ", "")
    aliases = {
        "1/1": "1:1",
        "4/5": "4:5",
        "9/16": "9:16",
        "16/9": "16:9",
    }
    raw = aliases.get(raw, raw)
    if raw not in ASPECT_SIZES:
        raise ValueError(f"Неподдерживаемый aspectRatio: {value}. Доступно: 1:1, 4:5, 9:16, 16:9")
    return raw


def canvas_size(aspect: str) -> tuple[int, int]:
    return ASPECT_SIZES[normalize_aspect(aspect)]


def _base(
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    fill: str,
    opacity: float = 1.0,
    angle: float = 0,
) -> dict[str, Any]:
    return {
        "version": FABRIC_VERSION,
        "originX": "left",
        "originY": "top",
        "stroke": None,
        "strokeWidth": 0,
        "strokeDashArray": None,
        "strokeLineCap": "butt",
        "strokeDashOffset": 0,
        "strokeLineJoin": "miter",
        "strokeUniform": False,
        "strokeMiterLimit": 4,
        "scaleX": 1,
        "scaleY": 1,
        "angle": angle,
        "flipX": False,
        "flipY": False,
        "opacity": opacity,
        "shadow": None,
        "visible": True,
        "backgroundColor": "",
        "fillRule": "nonzero",
        "paintFirst": "fill",
        "globalCompositeOperation": "source-over",
        "skewX": 0,
        "skewY": 0,
        "left": round(left, 2),
        "top": round(top, 2),
        "width": round(width, 2),
        "height": round(height, 2),
        "fill": fill,
    }


def textbox(
    text: str,
    *,
    left: float,
    top: float,
    width: float,
    font_size: int,
    font_family: str,
    fill: str,
    font_weight: str | int = "bold",
    font_style: str = "normal",
    text_align: str = "left",
    line_height: float = 1.05,
    char_spacing: int = 0,
    underline: bool = False,
    swibp_style: str = "body",
    swibp_slot: str = "text",
    swibp_role: str | None = None,
    height: float | None = None,
    angle: float = 0,
    opacity: float = 1.0,
    text_background: str = "",
) -> dict[str, Any]:
    lines = max(1, text.count("\n") + 1)
    computed_h = height if height is not None else round(font_size * line_height * lines)
    obj = _base(
        left=left,
        top=top,
        width=width,
        height=computed_h,
        fill=fill,
        opacity=opacity,
        angle=angle,
    )
    obj.update(
        {
            "type": "Textbox",
            "fontSize": font_size,
            "fontWeight": font_weight,
            "fontFamily": font_family,
            "fontStyle": font_style,
            "lineHeight": line_height,
            "text": text,
            "charSpacing": char_spacing,
            "textAlign": text_align,
            "styles": [],
            "pathStartOffset": 0,
            "pathSide": "left",
            "pathAlign": "baseline",
            "underline": underline,
            "overline": False,
            "linethrough": False,
            "textBackgroundColor": text_background,
            "direction": "ltr",
            "minWidth": 20,
            "splitByGrapheme": False,
            "swibpStyle": swibp_style,
            "swibpSlot": swibp_slot,
        }
    )
    if swibp_role:
        obj["swibpRole"] = swibp_role
    return obj


def rect(
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    fill: str,
    rx: float = 0,
    ry: float = 0,
    swibp_slot: str = "accent",
    opacity: float = 1.0,
    angle: float = 0,
) -> dict[str, Any]:
    obj = _base(
        left=left,
        top=top,
        width=width,
        height=height,
        fill=fill,
        opacity=opacity,
        angle=angle,
    )
    obj.update({"type": "Rect", "rx": rx, "ry": ry, "swibpSlot": swibp_slot})
    return obj


def image(
    src: str,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    swibp_slot: str = "image",
    opacity: float = 1.0,
) -> dict[str, Any]:
    """Fabric Image. Для data: URL crossOrigin не ставим (иначе CORS/canvas ломается)."""
    obj = _base(
        left=left,
        top=top,
        width=width,
        height=height,
        fill="",
        opacity=opacity,
    )
    obj.update(
        {
            "type": "Image",
            "src": src,
            "cropX": 0,
            "cropY": 0,
            "swibpSlot": swibp_slot,
        }
    )
    # remote URL — anonymous; data URL — без crossOrigin
    if not src.startswith("data:"):
        obj["crossOrigin"] = "anonymous"
    return obj


def slide(
    background: str,
    objects: list[dict[str, Any]],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    return {
        "version": FABRIC_VERSION,
        "background": background,
        "width": width,
        "height": height,
        "objects": objects,
    }
