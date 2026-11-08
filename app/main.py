from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import credits
from app.catalog import list_models, resolve_model_id
from app.content import generate_post_text
from app.cora import run_cora_fast
from app.generator import generate_carousel
from app.llm import complete as gateway_complete
from app.llm import health
from app.palette import generate_palette
from app.schemas import (
    CoraRunRequest,
    CreditsQuoteRequest,
    GatewayCompleteRequest,
    GeneratePaletteRequest,
    GeneratePostTextRequest,
    GeneratePostTextResponse,
    GenerateRequest,
    GenerateResponse,
    PaletteResponse,
    SetPlanRequest,
)

app = FastAPI(
    title="Deckva AI — CORA",
    description=(
        "CORA Fast + credits hub + OpenRouter model gateway. "
        "Без Ollama / BYOK — только OPENROUTER_API_KEY."
    ),
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck():
    return {"service": "ok", "openrouter": await health()}


@app.get("/models")
async def models(plan: str = Query("free", pattern="^(free|starter|pro)$")):
    rows = list_models(plan=plan)  # type: ignore[arg-type]
    return {
        "plan": plan,
        "models": [
            {
                "modelId": m.model_id,
                "displayName": m.display_name,
                "tier": m.tier,
                "baseCredits": m.base_credits,
                "openRouterSlug": m.open_router_slug,
                "enabled": m.enabled,
            }
            for m in rows
        ],
    }


@app.get("/credits/wallet/{user_id}")
async def wallet(user_id: str, plan: str = Query("free", pattern="^(free|starter|pro)$")):
    credits.ensure_wallet(user_id, plan=plan)  # type: ignore[arg-type]
    return {
        "userId": user_id,
        "plan": plan,
        "balance": credits.balance_of(user_id),
        "ledger": [
            {
                "id": e.id,
                "kind": e.kind,
                "amount": e.amount,
                "bucket": e.bucket,
                "generationId": e.generation_id,
                "holdId": e.hold_id,
                "createdAt": e.created_at,
                "meta": e.meta,
            }
            for e in credits.ledger_for(user_id)
        ],
    }


@app.post("/credits/quote")
async def quote(req: CreditsQuoteRequest):
    credits.ensure_wallet(req.user_id, plan=req.plan)
    try:
        model_id = resolve_model_id(req.plan, req.model_id)
    except (RuntimeError, PermissionError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    q = credits.quote(model_id=model_id, slides=req.slides, mode=req.mode)
    return {
        **q,
        "modelId": model_id,
        "wallet": credits.balance_of(req.user_id),
        "affordable": credits.balance_of(req.user_id)["total"] >= q["credits"],
    }


@app.post("/credits/plan")
async def set_plan(req: SetPlanRequest):
    wallet = credits.set_plan(req.user_id, req.plan)
    return {
        "userId": wallet.user_id,
        "plan": wallet.plan,
        "balance": credits.balance_of(req.user_id),
    }


@app.post("/cora/run")
async def cora_run(req: CoraRunRequest):
    try:
        return await run_cora_fast(req)
    except RuntimeError as exc:
        msg = str(exc)
        code = 402 if "кредит" in msg.lower() or "credits" in msg.lower() else 503
        if "не даёт доступ" in msg or "отключена" in msg or "Неизвестная модель" in msg:
            code = 403
        raise HTTPException(status_code=code, detail=msg) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"CORA failed: {exc}") from exc


@app.post("/internal/ai/complete")
async def internal_complete(req: GatewayCompleteRequest):
    try:
        return await gateway_complete(
            model_id=req.model_id,
            messages=req.messages,
            response_format=req.response_format,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Gateway failed: {exc}") from exc


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
        p = await generate_palette(
            topic=req.topic,
            language=req.language,
            model_id=req.model_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Palette failed: {exc}") from exc
    return PaletteResponse(**p.to_dict())


@app.post("/text", response_model=GeneratePostTextResponse)
async def text(req: GeneratePostTextRequest):
    try:
        result = await generate_post_text(req.post_text, model_id=req.model_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
    return GeneratePostTextResponse(text=result)
