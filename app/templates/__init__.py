"""Carousel visual templates (OOP registry)."""

from app.templates.base import CarouselTemplate
from app.templates.default import DefaultTemplate
from app.templates.registry import (
    build_carousel,
    get_template,
    list_skill_template_ids,
    register,
)

__all__ = [
    "CarouselTemplate",
    "DefaultTemplate",
    "build_carousel",
    "get_template",
    "list_skill_template_ids",
    "register",
]
