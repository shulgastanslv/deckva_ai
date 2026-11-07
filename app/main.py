from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.content import generate_post_text
from app.generator import generate_carousel
from app.llm import health
from app.palette import generate_palette
from app.schemas import (
    GeneratePaletteRequest,
    GeneratePostTextRequest,
    GeneratePostTextResponse,
    GenerateRequest,
    GenerateResponse,
    PaletteResponse,
)

app = FastAPI(
    title="Deckva Carousel AI",
    description="Карусели + палитра через Ollama qwen2.5:3b → Fabric JSON",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck():
    return {"service": "ok", "ollama": await health()}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    try:
        result = await generate_carousel(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    return GenerateResponse(
        title=result["title"],
        aspectRatio=result["aspectRatio"],
        width=result["width"],
        height=result["height"],
        path=result.get("path"),
        palette=result["palette"],
        carousel=result["carousel"],
    )


@app.post("/palette", response_model=PaletteResponse)
async def palette(req: GeneratePaletteRequest):
    try:
        p = await generate_palette(topic=req.topic, language=req.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Palette failed: {exc}") from exc
    return PaletteResponse(**p.to_dict())


@app.post("/text", response_model=GeneratePostTextResponse)
async def text(req: GeneratePostTextRequest):
    try:
        result = await generate_post_text(req.post_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
    return GeneratePostTextResponse(text=result)
