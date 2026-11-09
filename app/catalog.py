"""AiModelCatalog + plan ACL (in-memory Phase A)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

PlanId = Literal["free", "starter", "pro"]
ModelTier = Literal["economy", "standard", "premium"]

PLAN_RANK: dict[PlanId, int] = {"free": 0, "starter": 1, "pro": 2}
TIER_MIN_PLAN: dict[ModelTier, PlanId] = {
    "economy": "free",
    "standard": "starter",
    "premium": "starter",
}

DEFAULT_MODEL_BY_PLAN: dict[PlanId, str] = {
    "free": "gemini-flash",
    "starter": "claude-sonnet",
    "pro": "claude-sonnet",
}


@dataclass(frozen=True)
class AiModel:
    model_id: str
    display_name: str
    open_router_slug: str
    tier: ModelTier
    base_credits: int
    enabled: bool = True
    sort: int = 0


# Launch Economy subset + a few Standard/Premium rows for ACL demos.
# Slugs are catalog truth; update after OpenRouter sync without redeploying app logic.
_MODELS: tuple[AiModel, ...] = (
    AiModel("deepseek-v4-flash", "DeepSeek V4 Flash", "deepseek/deepseek-chat", "economy", 35, sort=10),
    AiModel("glm-flash", "GLM Flash", "z-ai/glm-4.5-air", "economy", 35, sort=20),
    AiModel("gemini-flash", "Gemini Flash", "google/gemini-2.5-flash", "economy", 40, sort=30),
    AiModel("gpt-mini", "GPT Mini", "openai/gpt-4o-mini", "economy", 45, sort=40),
    AiModel("claude-haiku", "Claude Haiku", "anthropic/claude-haiku-4.5", "economy", 50, sort=50),
    AiModel("qwen-flash", "Qwen Flash", "qwen/qwen-2.5-72b-instruct", "economy", 35, sort=60),
    AiModel("gpt-standard", "GPT Standard", "openai/gpt-4.1", "standard", 70, sort=110),
    AiModel("claude-sonnet", "Claude Sonnet", "anthropic/claude-sonnet-4.5", "standard", 90, sort=120),
    AiModel("gemini-pro", "Gemini Pro", "google/gemini-2.5-pro", "standard", 85, sort=130),
    AiModel("deepseek-pro", "DeepSeek Pro", "deepseek/deepseek-chat-v3-0324", "standard", 55, sort=140),
    AiModel("claude-opus", "Claude Opus", "anthropic/claude-opus-4.1", "premium", 160, sort=210),
    AiModel("gpt-pro", "GPT Pro", "openai/gpt-5", "premium", 180, sort=220),
)


def list_models(*, plan: PlanId | None = None, enabled_only: bool = True) -> list[AiModel]:
    rows = [m for m in _MODELS if m.enabled or not enabled_only]
    if plan is None:
        return sorted(rows, key=lambda m: m.sort)
    return sorted([m for m in rows if plan_allows_model(plan, m)], key=lambda m: m.sort)


def get_model(model_id: str) -> AiModel:
    for m in _MODELS:
        if m.model_id == model_id:
            if not m.enabled:
                raise RuntimeError(f"Модель отключена: {model_id}")
            return m
    raise RuntimeError(f"Неизвестная модель: {model_id}")


def plan_allows_model(plan: PlanId, model: AiModel) -> bool:
    min_plan = TIER_MIN_PLAN[model.tier]
    return PLAN_RANK[plan] >= PLAN_RANK[min_plan]


def resolve_model_id(plan: PlanId, model_id: str | None) -> str:
    if model_id:
        model = get_model(model_id)
        if not plan_allows_model(plan, model):
            raise PermissionError(
                f"План {plan} не даёт доступ к {model.model_id} (tier={model.tier}). Нужен {TIER_MIN_PLAN[model.tier]}."
            )
        return model.model_id
    return DEFAULT_MODEL_BY_PLAN[plan]


def quote_carousel_credits(*, model_id: str, slides: int, quality_mult: float = 1.0) -> int:
    model = get_model(model_id)
    slides_n = max(4, min(10, slides))
    raw = model.base_credits * (slides_n / 7.0) * quality_mult
    return max(1, math.ceil(raw))
