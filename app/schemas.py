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
    cover: str = Field(..., description="URL/путь обложки; пустая строка = placeholder")
    save: bool = Field(...)


class GeneratePostTextRequest(BaseModel):
    post_text: str = Field(..., min_length=2, max_length=4000)


class GeneratePostTextResponse(BaseModel):
    text: str


class PaletteResponse(BaseModel):
    name: str
    bg: str
    text: str
    muted: str
    accent: str
    accent_text: str
    grid: str
    photo: str


class GeneratePaletteRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)
    language: str = Field(..., min_length=2, max_length=8)


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
    cover: str
    slides: list[SlideContent]


class GenerateResponse(BaseModel):
    title: str
    aspectRatio: str
    width: int
    height: int
    path: str | None = None
    palette: PaletteResponse
    carousel: dict[str, Any]
