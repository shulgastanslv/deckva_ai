"""CarouselPlan scaffolding + object binding for Fast CORA."""

from __future__ import annotations

import hashlib
import random
from typing import Any

from app.schemas import SlideContent

# Moods steer palette + copy tone. CORA picks one per run.
_MOODS = (
    "soft_pastel_paper",
    "ink_on_cream",
    "midnight_editorial",
    "warm_terracotta",
    "cool_glacier",
    "bold_pop",
    "forest_moss",
    "sunset_coral",
    "mono_graphite",
    "lavender_haze",
    "matcha_editorial",
    "electric_contrast",
    "sand_and_ink",
    "berry_punch",
    "ocean_ink",
    "butter_yellow",
)

# Mid-slide role / fabric-layout pools (first/last are special).
_MID_ROLE_POOLS: tuple[tuple[str, ...], ...] = (
    ("hook", "offer", "proof", "howto", "checklist"),
    ("hook", "myth", "truth", "howto", "proof"),
    ("pain", "shift", "offer", "proof", "checklist"),
    ("hook", "list", "list", "quote", "proof"),
    ("story", "lesson", "howto", "proof", "offer"),
)

_MID_LAYOUT_POOLS: tuple[tuple[str, ...], ...] = (
    ("statement", "list", "list", "quote", "list"),
    ("statement", "quote", "list", "list", "statement"),
    ("list", "statement", "list", "quote", "list"),
    ("statement", "list", "quote", "list", "statement"),
    ("list", "list", "statement", "quote", "list"),
)

# Content layouts the LLM may emit for middle slides.
_CONTENT_LAYOUTS = ("statement", "orange_quote", "tips", "funnel", "results")


def _rng(cora_run_id: str, topic: str) -> random.Random:
    digest = hashlib.sha256(f"{cora_run_id}:{topic}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def decide_design(
    *,
    cora_run_id: str,
    topic: str,
    slides_count: int,
    skill_id: str | None = None,
    force_cover: bool = False,
) -> dict[str, Any]:
    """CORA Fast design choices for this run (deterministic per run id)."""
    from app.cora.skills import apply_skill_to_design

    rng = _rng(cora_run_id, topic)
    has_cover = rng.random() < 0.55
    mood = rng.choice(_MOODS)
    role_pool = list(rng.choice(_MID_ROLE_POOLS))
    layout_pool = list(rng.choice(_MID_LAYOUT_POOLS))
    rng.shuffle(role_pool)
    # Keep layout pool order but maybe reverse for variety
    if rng.random() < 0.4:
        layout_pool = list(reversed(layout_pool))

    # Sparse grid only — never stamp every slide ("all" retired).
    grid_mode = rng.choices(
        ("edges", "none", "cover_only", "cta_only"),
        weights=(0.38, 0.34, 0.18, 0.10),
        k=1,
    )[0]
    accent_bias = round(rng.uniform(0.25, 0.75), 2)
    photo_ratio = round(rng.uniform(0.38, 0.55), 2) if has_cover else None
    cover_placement = rng.choice(("top", "bottom", "left", "right"))
    cover_rounded = rng.random() < 0.30

    mid_roles: list[str] = []
    mid_layouts: list[str] = []
    mid_n = max(0, slides_count - 2)
    for i in range(mid_n):
        mid_roles.append(role_pool[i % len(role_pool)])
        mid_layouts.append(layout_pool[i % len(layout_pool)])

    design = {
        "hasCover": has_cover,
        "mood": mood,
        "gridMode": grid_mode,
        "accentBias": accent_bias,
        "photoRatio": photo_ratio,
        "coverPlacement": cover_placement,
        "coverRounded": cover_rounded,
        "midRoles": mid_roles,
        "midLayouts": mid_layouts,
        "preferredContentLayouts": list(_CONTENT_LAYOUTS),
    }
    return apply_skill_to_design(
        design,
        skill_id=skill_id,
        slides_count=slides_count,
        force_cover=force_cover,
    )


def _slide_role(index: int, slides_count: int, design: dict[str, Any]) -> str:
    if index == 0:
        return "cover" if design.get("hasCover") else "hook"
    if index == slides_count - 1:
        return "cta"
    mids: list[str] = design.get("midRoles") or []
    mid_i = index - 1
    if 0 <= mid_i < len(mids):
        return mids[mid_i]
    return "proof"


def _plan_layout(index: int, slides_count: int, design: dict[str, Any]) -> str:
    if index == 0:
        return "hero_cover" if design.get("hasCover") else "hero_text"
    if index == slides_count - 1:
        return "cta_end"
    mids: list[str] = design.get("midLayouts") or []
    mid_i = index - 1
    if 0 <= mid_i < len(mids):
        return mids[mid_i]
    return "statement"


def build_skeleton_plan(
    *,
    cora_run_id: str,
    mode: str,
    topic: str,
    language: str,
    ratio: str,
    slides_count: int,
    model_id: str,
    brand: dict[str, Any] | None = None,
    seed_text: str | None = None,
    design: dict[str, Any] | None = None,
) -> dict[str, Any]:
    n = int(slides_count)
    design = design or decide_design(cora_run_id=cora_run_id, topic=topic, slides_count=n)
    slides: list[dict[str, Any]] = []
    for i in range(n):
        role = _slide_role(i, n, design)
        objects: list[dict[str, Any]] = [
            {
                "id": f"s{i}_headline",
                "type": "text",
                "role": "headline",
                "brief": f"Headline for slide {i + 1} ({role}) about: {topic}",
            },
            {
                "id": f"s{i}_body",
                "type": "text",
                "role": "body" if role != "cta" else "cta",
                "brief": f"Supporting copy for slide {i + 1}",
            },
        ]
        if i == 0 and design.get("hasCover"):
            objects.append(
                {
                    "id": "s0_cover",
                    "type": "image",
                    "role": "cover",
                    "brief": "Cover mood photo; optional if no image provided",
                }
            )
        slides.append(
            {
                "index": i,
                "role": role,
                "layout": _plan_layout(i, n, design),
                "objects": objects,
            }
        )

    analysis = {
        "intent": "other",
        "language": language,
        "audience": "general",
        "hierarchy": ["hook", "offer", "proof", "cta"],
        "topic": topic,
        "mood": design["mood"],
        "hasCover": design["hasCover"],
    }
    if seed_text:
        analysis["seedTextPresent"] = True

    return {
        "version": 1,
        "coraRunId": cora_run_id,
        "mode": mode,
        "analysis": analysis,
        "design": design,
        "ratio": ratio,
        "slidesCount": n,
        "recommendedModelId": model_id,
        "brand": brand or {},
        "slides": slides,
        "jobs": [
            {
                "id": "j_fill",
                "tool": "llm.fill_and_layout",
                "modelId": model_id,
                "dependsOn": [],
                "input": {"slideIndexes": list(range(n))},
            }
        ],
    }


def bind_content_to_plan(plan: dict[str, Any], slides: list[SlideContent]) -> dict[str, Any]:
    """Fill object briefs/values from executed slide content; keep stable ids."""
    out = dict(plan)
    plan_slides = []
    for slide_meta in plan.get("slides", []):
        idx = int(slide_meta["index"])
        content = slides[idx] if idx < len(slides) else None
        objects = []
        for obj in slide_meta.get("objects", []):
            filled = dict(obj)
            if content is None:
                objects.append(filled)
                continue
            role = obj.get("role")
            if role == "headline":
                filled["value"] = content.heading
                filled["brief"] = content.heading
            elif role in {"body", "sub"}:
                filled["value"] = content.body or content.highlight
                filled["brief"] = filled["value"] or obj.get("brief", "")
            elif role == "cta":
                filled["value"] = content.body or content.heading
                filled["brief"] = filled["value"] or obj.get("brief", "")
            elif role == "cover":
                filled["value"] = content.image_prompt or None
            objects.append(filled)
        plan_slides.append({**slide_meta, "objects": objects, "fabricLayout": content.layout if content else None})
    out["slides"] = plan_slides
    return out


def object_bindings(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slide in plan.get("slides", []):
        for obj in slide.get("objects", []):
            if obj.get("type") != "text":
                continue
            rows.append(
                {
                    "objectId": obj["id"],
                    "slideIndex": slide["index"],
                    "role": obj.get("role"),
                    "value": obj.get("value", ""),
                }
            )
    return rows
