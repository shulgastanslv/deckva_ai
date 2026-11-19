"""AiModelCatalog + routing.

Slugs match OpenRouter model ids.
Daily generation limits live on Next.js — this service only lists models
and resolves OpenRouter slugs. No pro/free gating here.

Do NOT list `openrouter/free` (random router) or tiny <3B free models —
they often burn max_tokens on reasoning and return empty content for CORA JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelTier = Literal["economy", "standard", "premium"]

DEFAULT_MODEL_ID = "gemini-flash"


@dataclass(frozen=True)
class AiModel:
    model_id: str
    display_name: str
    open_router_slug: str
    tier: ModelTier
    enabled: bool = True
    sort: int = 0

    @property
    def credit_cost(self) -> int:
        """Credits per generation (mirrors deckva_web_client model-pricing)."""
        if self.tier == "premium":
            return 3
        if self.tier == "standard":
            return 2
        return 1


_MODELS: tuple[AiModel, ...] = (
    AiModel("gemini-flash-lite", "Gemini Flash Lite", "google/gemini-2.5-flash-lite", "economy", sort=20),
    AiModel("gemini-flash", "Gemini Flash", "google/gemini-2.5-flash", "economy", sort=30),
    AiModel("deepseek-chat", "DeepSeek Chat", "deepseek/deepseek-chat", "economy", sort=40),
    AiModel("gpt-4o-mini", "GPT-4o Mini", "openai/gpt-4o-mini", "economy", sort=50),
    AiModel("gpt-4.1-mini", "GPT-4.1 Mini", "openai/gpt-4.1-mini", "economy", sort=55),
    AiModel("claude-haiku", "Claude Haiku", "anthropic/claude-haiku-4.5", "economy", sort=60),
    AiModel("qwen-72b", "Qwen 2.5 72B", "qwen/qwen-2.5-72b-instruct", "economy", sort=70),
    AiModel("llama-3.3-70b", "Llama 3.3 70B", "meta-llama/llama-3.3-70b-instruct", "economy", sort=80),
    AiModel("gemini-pro", "Gemini Pro", "google/gemini-2.5-pro", "standard", sort=110),
    AiModel("deepseek-v3", "DeepSeek V3", "deepseek/deepseek-chat-v3-0324", "standard", sort=120),
    AiModel("claude-sonnet", "Claude Sonnet", "anthropic/claude-sonnet-4.5", "standard", sort=130),
    AiModel("gpt-4.1", "GPT-4.1", "openai/gpt-4.1", "standard", sort=140),
    AiModel("claude-opus", "Claude Opus", "anthropic/claude-opus-4.1", "premium", sort=210),
)


def list_models(*, enabled_only: bool = True) -> list[AiModel]:
    rows = [m for m in _MODELS if m.enabled or not enabled_only]
    return sorted(rows, key=lambda m: m.sort)


def get_model(model_id: str) -> AiModel:
    for m in _MODELS:
        if m.model_id == model_id:
            if not m.enabled:
                raise RuntimeError(f"Модель отключена: {model_id}")
            return m
    raise RuntimeError(f"Неизвестная модель: {model_id}")


def resolve_model_id(model_id: str | None) -> str:
    if model_id:
        return get_model(model_id).model_id
    return DEFAULT_MODEL_ID
