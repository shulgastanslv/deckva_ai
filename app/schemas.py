from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AspectRatio = Literal["1:1", "4:5", "9:16", "16:9"]
PlanId = Literal["free", "pro"]
CoraMode = Literal["fast", "thinking"]
CoraStatus = Literal["queued", "planning", "executing", "assembling", "done", "failed"]
SlideLayout = Literal[
    "cover",
    "statement",
    "orange_quote",
    "tips",
    "funnel",
    "results",
    "cta",
]


class BrandKit(BaseModel):
    palette: list[str] | None = None
    fonts: list[str] | None = None
    voice: str | None = None
    logo_asset_id: str | None = Field(None, alias="logoAssetId")

    model_config = {"populate_by_name": True}


class CoraAttachment(BaseModel):
    """Client attach: text notes → seed; images → cover / mid-slide photos."""

    name: str = Field("", max_length=256)
    kind: Literal["image", "text"] = "image"
    data_url: str | None = Field(None, alias="dataUrl")
    text: str | None = Field(None, max_length=8000)
    role: str | None = Field(
        None,
        description="Optional hint: cover | slide",
        max_length=32,
    )

    model_config = {"populate_by_name": True}


class CoraRunRequest(BaseModel):
    user_id: str = Field(..., alias="userId", min_length=1, max_length=128)
    topic: str = Field(..., min_length=2, max_length=800)
    language: str = Field(..., min_length=2, max_length=8)
    ratio: AspectRatio
    slides_count: int = Field(..., alias="slidesCount", ge=4, le=10)
    handle: str = Field(..., min_length=2, max_length=64)
    cover: str = Field("", description="URL/путь обложки; пустая строка = placeholder")
    mode: CoraMode = "fast"
    plan: PlanId = "free"
    model_id: str | None = Field(None, alias="modelId")
    brand_kit: BrandKit | None = Field(None, alias="brandKit")
    seed_text: str | None = Field(None, alias="seedText", max_length=8000)
    skill_id: str | None = Field(
        None,
        alias="skillId",
        description="launch|howto|offer|tips|story|comparison|checklist|myths|framework|pricing",
        max_length=32,
    )
    attachments: list[CoraAttachment] = Field(default_factory=list)
    stock_photos: bool = Field(
        True,
        alias="stockPhotos",
        description="Искать фото в Unsplash по image_prompt, если своих картинок нет",
    )
    save: bool = False

    model_config = {"populate_by_name": True}

class GatewayCompleteRequest(BaseModel):
    model_id: str = Field(..., alias="modelId")
    messages: list[dict[str, str]]
    response_format: str | None = Field("carousel_v1", alias="responseFormat")
    user_id: str | None = Field(None, alias="userId")
    cora_run_id: str | None = Field(None, alias="coraRunId")

    model_config = {"populate_by_name": True}


class PaletteResponse(BaseModel):
    name: str
    bg: str
    text: str
    muted: str
    accent: str
    accent_text: str
    grid: str
    photo: str


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


class CoraRunResponse(BaseModel):
    coraRunId: str
    status: CoraStatus
    mode: CoraMode
    modelId: str
    plan: dict[str, Any]
    objectBindings: list[dict[str, Any]] = Field(default_factory=list)
    title: str | None = None
    aspectRatio: str | None = None
    width: int | None = None
    height: int | None = None
    path: str | None = None
    palette: PaletteResponse | None = None
    carousel: dict[str, Any] | None = None
    error: str | None = None
    llmProvider: str | None = None
