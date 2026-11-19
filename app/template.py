"""Back-compat facade: carousel assemble via template registry.

Prefer `app.templates` for new code. Default template = original layout
when skill is unset; skill_id selects a registered skill template.
"""

from __future__ import annotations

from app.templates import (
    CarouselTemplate,
    DefaultTemplate,
    build_carousel,
    get_template,
    list_skill_template_ids,
    register,
)
from app.templates.base import (
    L,
    callout_block,
    clip,
    content_start_y,
    counter,
    footer,
    grid,
    handle_text as _handle,
    items_text as _items_text,
    make_layout as _L,
    meta_handle,
    stack_height as _stack_height,
    text_block as _text_block,
    text_h as _text_h,
    with_grid_for as _with_grid_for,
)

__all__ = [
    "CarouselTemplate",
    "DefaultTemplate",
    "L",
    "build_carousel",
    "callout_block",
    "clip",
    "content_start_y",
    "counter",
    "footer",
    "get_template",
    "grid",
    "list_skill_template_ids",
    "meta_handle",
    "register",
    "_L",
    "_handle",
    "_items_text",
    "_stack_height",
    "_text_block",
    "_text_h",
    "_with_grid_for",
]
