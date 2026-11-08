"""CarouselPlan scaffolding + object binding for Fast CORA."""

from __future__ import annotations

from typing import Any

from app.schemas import SlideContent

# cover → body slides → cta
_ROLE_SEQ = ("hook", "offer", "proof", "howto", "proof", "checklist", "cta")
_LAYOUT_SEQ = ("hero_text", "statement", "list", "list", "quote", "list", "cta_end")


def _slide_role(index: int, slides_count: int) -> str:
    if index == 0:
        return "cover"
    if index == slides_count - 1:
        return "cta"
    mid = _ROLE_SEQ[min(index, len(_ROLE_SEQ) - 1)]
    return mid


def _layout(index: int, slides_count: int) -> str:
    if index == 0:
        return "hero_text"
    if index == slides_count - 1:
        return "cta_end"
    return _LAYOUT_SEQ[min(index, len(_LAYOUT_SEQ) - 1)]


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
) -> dict[str, Any]:
    n = int(slides_count)
    slides: list[dict[str, Any]] = []
    for i in range(n):
        role = _slide_role(i, n)
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
        if i == 0:
            objects.append(
                {
                    "id": "s0_cover",
                    "type": "image",
                    "role": "cover",
                    "brief": "Optional cover mood; skip if no image tool",
                }
            )
        slides.append(
            {
                "index": i,
                "role": role,
                "layout": _layout(i, n),
                "objects": objects,
            }
        )

    analysis = {
        "intent": "other",
        "language": language,
        "audience": "general",
        "hierarchy": ["hook", "offer", "proof", "cta"],
        "topic": topic,
    }
    if seed_text:
        analysis["seedTextPresent"] = True

    return {
        "version": 1,
        "coraRunId": cora_run_id,
        "mode": mode,
        "analysis": analysis,
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
