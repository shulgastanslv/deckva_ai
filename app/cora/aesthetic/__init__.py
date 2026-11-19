"""CORA aesthetic branch: LLM invents Pinterest layouts (experiment).

Other skills keep the classic plan→template path. Only skillId=aesthetic
routes through this engine.
"""

from app.cora.aesthetic.assemble import assemble_aesthetic_carousel
from app.cora.aesthetic.generate import (
    generate_aesthetic_carousel,
    parse_aesthetic_raw,
    to_slide_contents,
)
from app.cora.aesthetic.photos import fill_aesthetic_photo_sets, seed_photo_sets_from_user

__all__ = [
    "assemble_aesthetic_carousel",
    "fill_aesthetic_photo_sets",
    "generate_aesthetic_carousel",
    "parse_aesthetic_raw",
    "seed_photo_sets_from_user",
    "to_slide_contents",
]
