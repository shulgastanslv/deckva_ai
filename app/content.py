"""Tool `llm.fill_and_layout`: тексты карусели через Model Gateway."""

from __future__ import annotations

from typing import Any

from app import prompts
from app.llm import chat_json
from app.schemas import SlideContent

VALID_LAYOUTS = {"cover", "statement", "orange_quote", "tips", "funnel", "results", "cta"}


def require_str(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise RuntimeError(f"ИИ не вернул обязательное поле: {field}")
    return text


def require_category(value: Any) -> str:
    text = require_str(value, "category")
    word = text.split()[0].strip(".,;:!?«»\"'")
    if not word:
        raise RuntimeError(f"category должна быть одним словом, получено: {text!r}")
    return word


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [p.strip(" -•→\t") for p in value.replace("|", "\n").split("\n") if p.strip()]
    return []


def parse_slides(slides_raw: Any, slides_count: int) -> list[SlideContent]:
    if slides_raw is None:
        raise RuntimeError("ИИ не вернул поле slides.")
    if not isinstance(slides_raw, list):
        raise RuntimeError("Поле slides должно быть массивом.")

    out: list[SlideContent] = []
    for i, item in enumerate(slides_raw):
        if not isinstance(item, dict):
            raise RuntimeError(f"Слайд #{i + 1}: ожидался объект.")
        heading = str(item.get("heading", "")).strip()
        if not heading:
            raise RuntimeError(f"Слайд #{i + 1}: пустой heading.")
        layout = str(item.get("layout", "")).strip()
        if layout not in VALID_LAYOUTS:
            raise RuntimeError(
                f"Слайд #{i + 1}: неверный layout '{layout}'. "
                f"Допустимо: {', '.join(sorted(VALID_LAYOUTS))}"
            )
        out.append(
            SlideContent(
                layout=layout,  # type: ignore[arg-type]
                heading=heading,
                highlight=str(item.get("highlight", "")).strip(),
                body=str(item.get("body", "")).strip(),
                items=_as_list(item.get("items")),
                badges=_as_list(item.get("badges")),
                flow=str(item.get("flow", "")).strip(),
                callout=str(item.get("callout", "")).strip(),
                tag=str(item.get("tag", "")).strip(),
                image_prompt=str(item.get("image_prompt", "")).strip(),
            )
        )
        if len(out) >= slides_count:
            break
    return out


def plan_briefs_text(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    for slide in plan.get("slides", []):
        idx = slide.get("index", 0)
        role = slide.get("role", "")
        layout = slide.get("layout", "")
        lines.append(f"- slide {idx} role={role} layout={layout}")
        for obj in slide.get("objects", []):
            if obj.get("type") != "text":
                continue
            lines.append(f"  · {obj.get('id')} [{obj.get('role')}]: {obj.get('brief', '')}")
    return "\n".join(lines)


async def fill_and_layout(
    *,
    topic: str,
    slides_count: int,
    language: str,
    handle: str,
    model_id: str,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """EXECUTE job: возвращает сырой carousel JSON от модели."""
    if not topic.strip():
        raise RuntimeError("Не указан topic.")
    if not handle.strip():
        raise RuntimeError("Не указан handle.")
    if not language.strip():
        raise RuntimeError("Не указан language.")
    if slides_count < 4:
        raise RuntimeError("slides_count должен быть >= 4.")

    briefs = plan_briefs_text(plan) if plan else ""
    return await chat_json(
        system=prompts.CAROUSEL_SYSTEM,
        user=prompts.carousel_user(
            topic=topic,
            language=language,
            slides_count=slides_count,
            handle=handle,
            plan_briefs=briefs,
        ),
        temperature=0.85,
        max_tokens=2800,
        model_id=model_id,
    )


async def generate_extra_slides(
    *,
    topic: str,
    count: int,
    language: str,
    handle: str,
    existing_headings: list[str],
    model_id: str,
) -> dict[str, Any]:
    if count < 1:
        raise RuntimeError("count для догенерации должен быть >= 1.")
    return await chat_json(
        system=prompts.CAROUSEL_SYSTEM,
        user=prompts.carousel_extra_user(
            topic=topic,
            language=language,
            count=count,
            handle=handle,
            existing_headings=existing_headings,
        ),
        temperature=0.9,
        max_tokens=1600,
        model_id=model_id,
    )


async def normalize_slides(
    raw: dict[str, Any],
    *,
    topic: str,
    slides_count: int,
    language: str,
    handle: str,
    model_id: str,
) -> list[SlideContent]:
    out = parse_slides(raw.get("slides"), slides_count)

    if 0 < len(out) < slides_count:
        need = slides_count - len(out)
        extra_raw = await generate_extra_slides(
            topic=topic,
            count=need,
            language=language,
            handle=handle,
            existing_headings=[s.heading for s in out],
            model_id=model_id,
        )
        extra = parse_slides(extra_raw.get("slides"), need)
        if len(extra) < need:
            raise RuntimeError(f"ИИ догенерировал {len(extra)} из {need} слайдов.")
        out.extend(extra[:need])

    if not out:
        raise RuntimeError("ИИ не вернул слайды.")
    if len(out) < slides_count:
        raise RuntimeError(f"ИИ вернул {len(out)} из {slides_count} слайдов.")

    out = out[:slides_count]
    out[0].layout = "cover"
    out[-1].layout = "cta"
    return out
