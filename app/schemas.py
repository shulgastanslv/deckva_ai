from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AspectRatio = Literal["1:1", "4:5", "9:16", "16:9"]
SlideLayout = Literal[
    "cover",
    "statement",
    "orange_quote",
    "tips",
    "funnel",
    "results",
    "cta",
]


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)
    aspect_ratio: AspectRatio = Field(..., description="1:1 | 4:5 | 9:16 | 16:9")
    slides_count: int = Field(..., ge=4, le=10)
    language: str = Field(..., min_length=2, max_length=8)
    handle: str = Field(..., min_length=2, max_length=64)
    category: str = Field(..., min_length=1, max_length=64)
    save: bool = Field(...)


class SlideContent(BaseModel):
    layout: SlideLayout
    heading: str
    highlight: str = ""
    body: str = ""
    items: list[str] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    flow: str = ""
    callout: str = ""
    tag: str = ""
    image_prompt: str = ""


class CarouselContent(BaseModel):
    title: str
    tagline: str
    handle: str
    category: str
    slides: list[SlideContent]


class GenerateResponse(BaseModel):
    title: str
    aspectRatio: str
    width: int
    height: int
    path: str | None = None
    carousel: dict[str, Any]
