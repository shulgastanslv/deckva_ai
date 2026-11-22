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


def group(
    objects: list[dict[str, Any]],
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    opacity: float = 1.0,
    swibp_role: str | None = None,
    swibp_name: str | None = None,
    swibp_slot: str | None = None,
) -> dict[str, Any]:
    """Fabric Group. Children use coords relative to the group center."""
    gw = float(width)
    gh = float(height)
    cx = gw / 2.0
    cy = gh / 2.0
    children: list[dict[str, Any]] = []
    for raw in objects:
        child = dict(raw)
        child["left"] = round(float(child.get("left", 0)) - cx, 2)
        child["top"] = round(float(child.get("top", 0)) - cy, 2)
        children.append(child)

    obj = _base(
        left=left,
        top=top,
        width=gw,
        height=gh,
        fill="",
        opacity=opacity,
    )
    obj.update(
        {
            "type": "Group",
            "subTargetCheck": False,
            "interactive": False,
            # Omit layoutManager — Fabric builds a default; serialized
            # "layoutManager" breaks after client lowercases object types.
            "objects": children,
        }
    )
    if swibp_role:
        obj["swibpRole"] = swibp_role
    if swibp_name:
        obj["swibpName"] = swibp_name
    if swibp_slot:
        obj["swibpSlot"] = swibp_slot
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
    rx: float = 0,
    ry: float = 0,
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
    radius_x = max(0.0, float(rx))
    radius_y = max(0.0, float(ry) if ry else radius_x)
    if radius_x > 0 or radius_y > 0:
        obj["clipPath"] = {
            "type": "Rect",
            "version": FABRIC_VERSION,
            "originX": "center",
            "originY": "center",
            "left": 0,
            "top": 0,
            "width": round(width, 2),
            "height": round(height, 2),
            "fill": "#000000",
            "stroke": None,
            "strokeWidth": 0,
            "rx": round(radius_x, 2),
            "ry": round(radius_y, 2),
            "scaleX": 1,
            "scaleY": 1,
            "angle": 0,
            "flipX": False,
            "flipY": False,
            "opacity": 1,
            "visible": True,
            "backgroundColor": "",
            "fillRule": "nonzero",
            "paintFirst": "fill",
            "globalCompositeOperation": "source-over",
            "skewX": 0,
            "skewY": 0,
            "shadow": None,
        }
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
