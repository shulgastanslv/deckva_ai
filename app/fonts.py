"""Каталог шрифтов 2026 + типографика (ИИ выбирает family и scale)."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass
from typing import Any

from app import prompts
from app.llm import chat_json

# 20 Google Fonts с кириллицей + латиницей (ru/en карусели)
FONT_CATALOG: tuple[str, ...] = (
    "Inter",
    "Poppins",
    "Montserrat",
    "Roboto",
    "Open Sans",
    "Lato",
    "Manrope",
    "Nunito",
    "Rubik",
    "Onest",
    "Raleway",
    "Ubuntu",
    "Noto Sans",
    "IBM Plex Sans",
    "Playfair Display",
    "Lora",
    "Merriweather",
    "PT Serif",
    "Oswald",
    "Unbounded",
)

_FONT_BY_LOWER = {f.lower(): f for f in FONT_CATALOG}

HEAD_SIZE_MAX = 70
BODY_SIZE_MAX = 36
META_SIZE_MAX = 24

# Именованные шкалы: абсолютные размеры для default-шаблона.
# Skill-шаблоны масштабируются относительно SIZE_HEAD/BODY/META.
TYPE_SCALES: dict[str, dict[str, int]] = {
    "compact": {"head": 44, "body": 22, "meta": 16},
    "balanced": {"head": 55, "body": 25, "meta": 20},
    "editorial": {"head": 64, "body": 24, "meta": 18},
    "display": {"head": 70, "body": 26, "meta": 18},
    "dense": {"head": 48, "body": 20, "meta": 16},
    "airy": {"head": 58, "body": 28, "meta": 20},
    "poster": {"head": 70, "body": 24, "meta": 18},
    "magazine": {"head": 60, "body": 23, "meta": 17},
}

DEFAULT_SCALE_ID = "balanced"
BASE_HEAD = 55
BASE_BODY = 25
BASE_META = 20


@dataclass(frozen=True)
class Typography:
    font_family: str = "Montserrat"
    type_scale: str = DEFAULT_SCALE_ID
    head_size: int = BASE_HEAD
    body_size: int = BASE_BODY
    meta_size: int = BASE_META
    show_handle: bool = True

    @property
    def head_scale(self) -> float:
        return self.head_size / BASE_HEAD

    @property
    def body_scale(self) -> float:
        return self.body_size / BASE_BODY

    @property
    def meta_scale(self) -> float:
        return self.meta_size / BASE_META

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "fontFamily": self.font_family,
            "typeScale": self.type_scale,
            "headSize": self.head_size,
            "bodySize": self.body_size,
            "metaSize": self.meta_size,
            "showHandle": self.show_handle,
        }


DEFAULT_TYPOGRAPHY = Typography()

_typo_ctx: ContextVar[Typography] = ContextVar("typography", default=DEFAULT_TYPOGRAPHY)


def current_typography() -> Typography:
    return _typo_ctx.get()


def current_font() -> str:
    return _typo_ctx.get().font_family


def push_typography(typo: Typography) -> Token:
    return _typo_ctx.set(typo)


def reset_typography(token: Token) -> None:
    _typo_ctx.reset(token)


def list_fonts() -> list[dict[str, str]]:
    return [{"id": f, "family": f} for f in FONT_CATALOG]


def resolve_font(name: str | None) -> str | None:
    if not name or not str(name).strip():
        return None
    key = str(name).strip().lower()
    return _FONT_BY_LOWER.get(key)


def _sizes_for_scale(scale_id: str) -> dict[str, int]:
    return dict(TYPE_SCALES.get(scale_id, TYPE_SCALES[DEFAULT_SCALE_ID]))


def parse_typography(
    raw: dict[str, Any] | None,
    *,
    show_handle: bool = True,
    font_override: str | None = None,
) -> Typography:
    data = raw if isinstance(raw, dict) else {}
    font = resolve_font(font_override) or resolve_font(str(data.get("fontFamily") or data.get("font") or ""))
    if not font:
        font = DEFAULT_TYPOGRAPHY.font_family

    scale_raw = str(data.get("typeScale") or data.get("type_scale") or DEFAULT_SCALE_ID).strip().lower()
    if scale_raw not in TYPE_SCALES:
        scale_raw = DEFAULT_SCALE_ID
    sizes = _sizes_for_scale(scale_raw)

    def _int(key_camel: str, key_snake: str, fallback: int, lo: int, hi: int) -> int:
        val = data.get(key_camel, data.get(key_snake))
        if val is None:
            return fallback
        try:
            n = int(val)
        except (TypeError, ValueError):
            return fallback
        return max(lo, min(hi, n))

    return Typography(
        font_family=font,
        type_scale=scale_raw,
        head_size=_int("headSize", "head_size", sizes["head"], 32, HEAD_SIZE_MAX),
        body_size=_int("bodySize", "body_size", sizes["body"], 16, BODY_SIZE_MAX),
        meta_size=_int("metaSize", "meta_size", sizes["meta"], 12, META_SIZE_MAX),
        show_handle=bool(show_handle),
    )


async def generate_typography(
    *,
    topic: str,
    language: str,
    mood: str = "",
    model_id: str | None = None,
    show_handle: bool = True,
    font_override: str | None = None,
) -> Typography:
    """ИИ выбирает шрифт из каталога и подходящую шкалу размеров."""
    if font_override and resolve_font(font_override):
        # Пользователь задал шрифт — ИИ только scale
        raw = await chat_json(
            system=prompts.TYPOGRAPHY_SYSTEM,
            user=prompts.typography_user(
                topic=topic,
                language=language,
                mood=mood,
                fonts=FONT_CATALOG,
                scales=tuple(TYPE_SCALES.keys()),
                font_locked=resolve_font(font_override),
            ),
            temperature=0.9,
            max_tokens=300,
            model_id=model_id,
        )
        return parse_typography(raw, show_handle=show_handle, font_override=font_override)

    raw = await chat_json(
        system=prompts.TYPOGRAPHY_SYSTEM,
        user=prompts.typography_user(
            topic=topic,
            language=language,
            mood=mood,
            fonts=FONT_CATALOG,
            scales=tuple(TYPE_SCALES.keys()),
        ),
        temperature=0.95,
        max_tokens=300,
        model_id=model_id,
    )
    return parse_typography(raw, show_handle=show_handle, font_override=None)


def scaled_size(base: int, *, kind: str = "head") -> int:
    """Масштабировать размер шаблона относительно базовой шкалы ИИ."""
    t = current_typography()
    if kind == "body":
        return max(14, min(BODY_SIZE_MAX, round(base * t.body_scale)))
    if kind == "meta":
        return max(12, min(META_SIZE_MAX, round(base * t.meta_scale)))
    return max(28, min(HEAD_SIZE_MAX, round(base * t.head_scale)))
