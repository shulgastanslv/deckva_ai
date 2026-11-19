"""Генерация и валидация цветовой палитры."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from app import prompts
from app.llm import chat_json

_HEX = re.compile(r"^#([0-9A-Fa-f]{6})$")


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    text: str
    muted: str
    accent: str
    accent_text: str
    grid: str
    photo: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


DEFAULT_PALETTE = Palette(
    name="quiet_paper",
    bg="#FFFFFF",
    text="#111111",
    muted="#9A9A9A",
    accent="#F6C1C0",
    accent_text="#2A2A2A",
    grid="#CFCFCF",
    photo="#C8C8C8",
)


def _hex(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not _HEX.match(text):
        raise RuntimeError(f"Палитра: поле {field} должно быть hex #RRGGBB, получено {text!r}")
    return text.upper()


def _rel_luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float:
    l1, l2 = _rel_luminance(a), _rel_luminance(b)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


def _ensure_readable(fg: str, bg: str, *, prefer_light: bool | None = None) -> str:
    """If contrast is weak, flip toward black/white on bg."""
    if _contrast_ratio(fg, bg) >= 3.0:
        return fg
    if prefer_light is None:
        prefer_light = _rel_luminance(bg) < 0.45
    return "#F5F5F5" if prefer_light else "#141414"


def parse_palette(raw: dict[str, Any]) -> Palette:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise RuntimeError("ИИ не вернул name палитры.")
    bg = _hex(raw.get("bg"), "bg")
    text = _ensure_readable(_hex(raw.get("text"), "text"), bg)
    accent = _hex(raw.get("accent"), "accent")
    accent_text = _ensure_readable(_hex(raw.get("accent_text"), "accent_text"), accent)
    return Palette(
        name=name[:48],
        bg=bg,
        text=text,
        muted=_hex(raw.get("muted"), "muted"),
        accent=accent,
        accent_text=accent_text,
        grid=_hex(raw.get("grid"), "grid"),
        photo=_hex(raw.get("photo"), "photo"),
    )


async def generate_palette(
    *,
    topic: str,
    language: str,
    model_id: str | None = None,
    mood: str = "",
) -> Palette:
    if not topic.strip():
        raise RuntimeError("Не указан topic для палитры.")
    if not language.strip():
        raise RuntimeError("Не указан language для палитры.")

    raw = await chat_json(
        system=prompts.PALETTE_SYSTEM,
        user=prompts.palette_user(topic=topic, language=language, mood=mood),
        temperature=1.05,
        max_tokens=400,
        model_id=model_id,
    )
    return parse_palette(raw)
