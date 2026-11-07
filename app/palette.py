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


def parse_palette(raw: dict[str, Any]) -> Palette:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise RuntimeError("ИИ не вернул name палитры.")
    return Palette(
        name=name[:48],
        bg=_hex(raw.get("bg"), "bg"),
        text=_hex(raw.get("text"), "text"),
        muted=_hex(raw.get("muted"), "muted"),
        accent=_hex(raw.get("accent"), "accent"),
        accent_text=_hex(raw.get("accent_text"), "accent_text"),
        grid=_hex(raw.get("grid"), "grid"),
        photo=_hex(raw.get("photo"), "photo"),
    )


async def generate_palette(*, topic: str, language: str) -> Palette:
    if not topic.strip():
        raise RuntimeError("Не указан topic для палитры.")
    if not language.strip():
        raise RuntimeError("Не указан language для палитры.")

    raw = await chat_json(
        system=prompts.PALETTE_SYSTEM,
        user=prompts.palette_user(topic=topic, language=language),
        temperature=0.7,
        num_predict=400,
    )
    return parse_palette(raw)
