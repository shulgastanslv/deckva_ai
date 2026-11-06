from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.generator import generate_carousel
from app.ollama_client import health, generate_post_text_content
from app.schemas import GenerateRequest, GenerateResponse, GeneratePostTextRequest, GeneratePostTextResponse

app = FastAPI(
    title="Deckva Carousel AI",
    description="Генерация каруселей (фото сверху + сетка + акцент) через Ollama qwen2.5:3b → Fabric JSON",
    version="0.2.0",
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
        carousel=result["carousel"],
    )


@app.post("/text", response_model=GeneratePostTextResponse)
async def generate_post_text(req: GeneratePostTextRequest):
    try:
        result = await generate_post_text_content(req.post_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    return GeneratePostTextResponse(text=result)