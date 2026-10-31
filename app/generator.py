from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from app.ollama_client import generate_content, generate_extra_slides
from app.schemas import CarouselContent, GenerateRequest, SlideContent
from app.template import build_carousel

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

VALID_LAYOUTS = {"cover", "statement", "orange_quote", "tips", "funnel", "results", "cta"}


def _slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    if not text:
        raise RuntimeError("Не удалось сформировать имя файла из title.")
    return text[:48]


def _require_str(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise RuntimeError(f"ИИ не вернул обязательное поле: {field}")
    return text


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        parts = re.split(r"[\n;|]+", value)
        return [p.strip(" -•→\t") for p in parts if p.strip()]
    return []


def _parse_slides(slides_raw: Any, slides_count: int) -> list[SlideContent]:
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


async def _normalize_slides(raw: dict[str, Any], req: GenerateRequest) -> list[SlideContent]:
    out = _parse_slides(raw.get("slides"), req.slides_count)

    if 0 < len(out) < req.slides_count:
        need = req.slides_count - len(out)
        extra_raw = await generate_extra_slides(
            req.topic,
            count=need,
            language=req.language,
            existing_headings=[s.heading for s in out],
            handle=req.handle,
            category=req.category,
        )
        extra = _parse_slides(extra_raw.get("slides"), need)
        if len(extra) < need:
            raise RuntimeError(
                f"ИИ догенерировал {len(extra)} из {need} недостающих слайдов."
            )
        out.extend(extra[:need])

    if not out:
        raise RuntimeError("ИИ не вернул слайды. Проверь Ollama / qwen2.5:3b.")

    if len(out) < req.slides_count:
        raise RuntimeError(
            f"ИИ вернул {len(out)} из {req.slides_count} слайдов. Повтори запрос."
        )

    out = out[: req.slides_count]
    if out[0].layout != "cover":
        raise RuntimeError("Первый слайд должен иметь layout=cover.")
    if out[-1].layout != "cta":
        raise RuntimeError("Последний слайд должен иметь layout=cta.")
    return out


async def _to_content(raw: dict[str, Any], req: GenerateRequest) -> CarouselContent:
    return CarouselContent(
        title=_require_str(raw.get("title"), "title"),
        tagline=str(raw.get("tagline", "")).strip(),
        handle=req.handle,
        category=req.category,
        slides=await _normalize_slides(raw, req),
    )


async def generate_carousel(req: GenerateRequest) -> dict[str, Any]:
    raw = await generate_content(
        req.topic,
        slides_count=req.slides_count,
        language=req.language,
        handle=req.handle,
        category=req.category,
    )
    content = await _to_content(raw, req)
    seed = int(time.time() * 1000) % 2_147_483_647
    carousel = build_carousel(content, aspect_ratio=req.aspect_ratio, seed=seed)

    path: str | None = None
    if req.save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / f"{int(time.time())}_{_slug(content.title)}.json"
        public = {
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "slides": carousel["slides"],
        }
        out.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
        path = str(out)

    return {
        "title": content.title,
        "aspectRatio": carousel["aspectRatio"],
        "width": carousel["width"],
        "height": carousel["height"],
        "path": path,
        "carousel": {
            "title": carousel["title"],
            "aspectRatio": carousel["aspectRatio"],
            "width": carousel["width"],
            "height": carousel["height"],
            "slides": carousel["slides"],
        },
    }
