from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import credits
from app.catalog import list_models, resolve_model_id
from app.cora import get_run, list_runs_for_user, run_cora_fast
from app.llm import complete as gateway_complete
from app.llm import health
from app.schemas import (
    CoraRunRequest,
    CoraRunResponse,
    CreditsQuoteRequest,
    GatewayCompleteRequest,
    SetPlanRequest,
)

app = FastAPI(
    title="Deckva AI — CORA",
    description=(
        "CORA Fast + credits hub + OpenRouter gateway. "
        "Единый путь генерации: POST /cora/run. Без Ollama / BYOK."
    ),
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _http_for_cora_error(msg: str) -> int:
    low = msg.lower()
    if "кредит" in low or "credits" in low or "недостаточно" in low:
        return 402
    if "не даёт доступ" in msg or "отключена" in msg or "Неизвестная модель" in msg:
        return 403
    return 503


@app.get("/health")
async def healthcheck():
    return {
        "service": "ok",
        "version": app.version,
        "llmProvider": "openrouter",
        "gateway": await health(),
    }


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
    w = credits.ensure_wallet(user_id, plan=plan)  # type: ignore[arg-type]
    return {
        "userId": user_id,
        "plan": w.plan,
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
    bal = credits.balance_of(req.user_id)
    return {
        **q,
        "modelId": model_id,
        "wallet": bal,
        "affordable": bal["total"] >= q["credits"],
    }


@app.post("/credits/plan")
async def set_plan(req: SetPlanRequest):
    wallet = credits.set_plan(req.user_id, req.plan)
    return {
        "userId": wallet.user_id,
        "plan": wallet.plan,
        "balance": credits.balance_of(req.user_id),
    }


@app.post("/cora/run", response_model=CoraRunResponse)
async def cora_run(req: CoraRunRequest) -> CoraRunResponse:
    try:
        return await run_cora_fast(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=_http_for_cora_error(str(exc)), detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"CORA failed: {exc}") from exc


@app.get("/cora/runs/{cora_run_id}")
async def cora_get(cora_run_id: str):
    row = get_run(cora_run_id)
    if not row:
        raise HTTPException(status_code=404, detail="CORA run not found")
    return row


@app.get("/cora/runs")
async def cora_list(userId: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    return {"userId": userId, "runs": list_runs_for_user(userId, limit=limit)}


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
