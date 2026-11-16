"""Template registry: skill_id → CarouselTemplate. Extensible via register()."""

from __future__ import annotations

from typing import Any

from app.palette import Palette
from app.schemas import CarouselContent
from app.templates.base import CarouselTemplate
from app.templates.default import DefaultTemplate
from app.templates.skills import SKILL_TEMPLATE_CLASSES

_DEFAULT = DefaultTemplate()
_BY_SKILL: dict[str, CarouselTemplate] = {}


def register(template: CarouselTemplate) -> None:
    """Register (or replace) a skill template. skill_id must be set."""
    key = template.skill_id
    if not key:
        raise ValueError("Only skill templates can be registered (skill_id required).")
    _BY_SKILL[key.strip().lower()] = template


def _bootstrap() -> None:
    if _BY_SKILL:
        return
    for cls in SKILL_TEMPLATE_CLASSES:
        register(cls())


def get_template(skill_id: str | None = None) -> CarouselTemplate:
    """Resolve template. Unknown / empty skill → default (current) template."""
    _bootstrap()
    if not skill_id:
        return _DEFAULT
    key = skill_id.strip().lower()
    return _BY_SKILL.get(key, _DEFAULT)


def list_skill_template_ids() -> list[str]:
    _bootstrap()
    return sorted(_BY_SKILL.keys())


def build_carousel(
    content: CarouselContent,
    *,
    aspect_ratio: str,
    palette: Palette,
    seed: int | None = None,
    design: dict[str, Any] | None = None,
    slide_photos: list[str] | None = None,
    skill_id: str | None = None,
) -> dict[str, Any]:
    design = design or {}
    sid = skill_id if skill_id is not None else design.get("skillId")
    if isinstance(sid, str):
        sid = sid.strip() or None
    else:
        sid = None
    template = get_template(sid)
    return template.build_carousel(
        content,
        aspect_ratio=aspect_ratio,
        palette=palette,
        seed=seed,
        design=design,
        slide_photos=slide_photos,
    )
