from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.catalog import list_models, resolve_model_id
from app.cora import get_run, list_runs_for_user, run_cora_fast
from app.llm import complete as gateway_complete
from app.llm import health
from app.schemas import (
    CoraRunRequest,
    CoraRunResponse,
    GatewayCompleteRequest,
)

app = FastAPI(
    title="Deckva AI — CORA",
    description=(
        "CORA Fast + OpenRouter gateway. "
        "Единый путь генерации: POST /cora/run. Без Ollama / BYOK. "
        "Подписка / лимит генераций — на Next.js сервере."
    ),
    version="0.7.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _http_for_cora_error(msg: str) -> int:
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
async def models(plan: str = Query("free", pattern="^(free|pro)$")):
    rows = list_models(plan=plan)  # type: ignore[arg-type]
    return {
        "plan": plan,
        "models": [
            {
                "modelId": m.model_id,
                "displayName": m.display_name,
                "tier": m.tier,
                "openRouterSlug": m.open_router_slug,
                "enabled": m.enabled,
                "isFree": False,
                "creditCost": m.credit_cost,
            }
            for m in rows
        ],
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
