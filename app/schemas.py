from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AspectRatio = Literal["1:1", "4:5", "9:16", "16:9"]
PlanId = Literal["free", "starter", "pro"]
CoraMode = Literal["fast", "thinking"]
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
    model_id: str | None = Field(None, alias="modelId")
    user_id: str | None = Field(None, alias="userId")

    model_config = {"populate_by_name": True}


class GeneratePostTextRequest(BaseModel):
    post_text: str = Field(..., min_length=2, max_length=4000)
    model_id: str | None = Field(None, alias="modelId")

    model_config = {"populate_by_name": True}


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
    model_id: str | None = Field(None, alias="modelId")

    model_config = {"populate_by_name": True}


class BrandKit(BaseModel):
    palette: list[str] | None = None
    fonts: list[str] | None = None
    voice: str | None = None
    logo_asset_id: str | None = Field(None, alias="logoAssetId")

    model_config = {"populate_by_name": True}


class CoraRunRequest(BaseModel):
    user_id: str = Field(..., alias="userId", min_length=1, max_length=128)
    topic: str = Field(..., min_length=2, max_length=300)
    language: str = Field(..., min_length=2, max_length=8)
    ratio: AspectRatio = Field(..., description="1:1 | 4:5 | 9:16 | 16:9")
    slides_count: int = Field(..., alias="slidesCount", ge=4, le=10)
    handle: str = Field(..., min_length=2, max_length=64)
    cover: str = Field(..., description="URL/путь обложки; пустая строка = placeholder")
    mode: CoraMode = "fast"
    plan: PlanId = "free"
    model_id: str | None = Field(None, alias="modelId")
    brand_kit: BrandKit | None = Field(None, alias="brandKit")
    seed_text: str | None = Field(None, alias="seedText", max_length=8000)
    save: bool = False

    model_config = {"populate_by_name": True}


class CreditsQuoteRequest(BaseModel):
    user_id: str = Field(..., alias="userId")
    model_id: str = Field(..., alias="modelId")
    slides: int = Field(..., ge=4, le=10)
    mode: CoraMode = "fast"
    plan: PlanId = "free"

    model_config = {"populate_by_name": True}


class SetPlanRequest(BaseModel):
    user_id: str = Field(..., alias="userId")
    plan: PlanId

    model_config = {"populate_by_name": True}


class GatewayCompleteRequest(BaseModel):
    model_id: str = Field(..., alias="modelId")
    messages: list[dict[str, str]]
    response_format: str | None = Field("carousel_v1", alias="responseFormat")
    user_id: str | None = Field(None, alias="userId")
    cora_run_id: str | None = Field(None, alias="coraRunId")

    model_config = {"populate_by_name": True}


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
