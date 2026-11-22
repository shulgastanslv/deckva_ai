"""Editorial reference templates — single Aesthetic skill.

Former manifesto / niches / lookbook skills are cover variants inside
AestheticTemplate (server RNG). Legacy skillIds alias to `aesthetic`.
"""

from __future__ import annotations

from app.templates.aesthetic import AestheticTemplate
from app.templates.default import DefaultTemplate

REFERENCE_SKILL_TEMPLATE_CLASSES: list[type[DefaultTemplate]] = [
    AestheticTemplate,
]

__all__ = [
    "AestheticTemplate",
    "REFERENCE_SKILL_TEMPLATE_CLASSES",
]
