"""Model Gateway: Deckva modelId → OpenRouter. Без Ollama / BYOK / локальных весов."""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
from typing import Any

import httpx

from app.catalog import get_model

OPENROUTER_BASE = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
DEFAULT_TIMEOUT = float(os.getenv("OPENROUTER_TIMEOUT", "180"))
DEFAULT_MODEL_ID = os.getenv("DECKVA_DEFAULT_MODEL_ID", "gemini-flash")
LLM_MAX_RETRIES = max(0, int(os.getenv("OPENROUTER_MAX_RETRIES", "4")))
LLM_RETRY_BASE_SEC = float(os.getenv("OPENROUTER_RETRY_BASE_SEC", "1.25"))


def openrouter_api_key() -> str:
    return (os.getenv("OPENROUTER_API_KEY") or "").strip()


def require_api_key() -> str:
    key = openrouter_api_key()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY не задан. Все LLM-вызовы идут только через OpenRouter."
        )
    return key


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise RuntimeError(f"Ответ не JSON: {text[:200]!r}")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise RuntimeError("JSON-ответ должен быть объектом.")
    return data


def resolve_slug(model_id: str | None = None) -> tuple[str, str]:
    mid = model_id or DEFAULT_MODEL_ID
    model = get_model(mid)
    return model.model_id, model.open_router_slug


def _retry_delay_sec(attempt: int, resp: httpx.Response | None = None) -> float:
    """Backoff for 429/5xx. Honors Retry-After when present."""
    if resp is not None:
        raw = (resp.headers.get("Retry-After") or "").strip()
        if raw:
            try:
                return max(0.5, min(60.0, float(raw)))
            except ValueError:
                pass
    # attempt 0 → ~1.25s, then 2.5, 5, 10… + jitter
    base = LLM_RETRY_BASE_SEC * (2**attempt)
    jitter = random.uniform(0.0, 0.35 * base)
    return min(45.0, base + jitter)


async def chat(
    *,
    system: str,
    user: str,
    as_json: bool = True,
    temperature: float = 0.85,
    top_p: float = 0.92,
    max_tokens: int = 4096,
    model_id: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    key = require_api_key()
    resolved_id, slug = resolve_slug(model_id)
    payload: dict[str, Any] = {
        "model": slug,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    if as_json:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://deckva.app"),
        "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Deckva CORA"),
    }

    last_status = 0
    async with httpx.AsyncClient(base_url=OPENROUTER_BASE, timeout=timeout) as client:
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                resp = await client.post("/chat/completions", json=payload, headers=headers)
            except httpx.ConnectError as exc:
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(_retry_delay_sec(attempt))
                    continue
                raise RuntimeError("OpenRouter недоступен (connect error).") from exc
            except httpx.ReadTimeout as exc:
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(_retry_delay_sec(attempt))
                    continue
                raise RuntimeError("OpenRouter не успел ответить. Повтори запрос.") from exc

            last_status = resp.status_code
            if resp.status_code in {429, 500, 502, 503, 504}:
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(_retry_delay_sec(attempt, resp))
                    continue
                if resp.status_code == 429:
                    raise RuntimeError(
                        "OpenRouter 429: rate limit после повторов. Подожди и попробуй снова."
                    )
                raise RuntimeError(f"OpenRouter {resp.status_code}: upstream error после повторов.")

            if resp.status_code >= 400:
                raise RuntimeError(
                    f"OpenRouter {resp.status_code} ({resolved_id}/{slug}): {resp.text[:300]}"
                )

            data = resp.json()
            try:
                choice = data["choices"][0]
                message_obj = choice["message"]
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Пустой/битый ответ OpenRouter: {data}") from exc

            content = message_obj.get("content") if isinstance(message_obj, dict) else None
            if isinstance(content, str) and content.strip():
                return content.strip()

            # Some free/reasoning models dump JSON into `reasoning` and leave content empty.
            reasoning = message_obj.get("reasoning") if isinstance(message_obj, dict) else None
            if isinstance(reasoning, str) and "{" in reasoning:
                match = re.search(r"\{.*\}", reasoning, re.DOTALL)
                if match:
                    return match.group(0).strip()

            finish = choice.get("finish_reason") or choice.get("native_finish_reason")
            model_name = data.get("model") or slug
            if finish == "length":
                raise RuntimeError(
                    f"Модель {model_name} обрезала ответ (finish_reason=length) без JSON. "
                    "Выбери более крупную модель (Gemini Flash / Claude Sonnet)."
                )
            raise RuntimeError(
                f"Пустой ответ OpenRouter ({model_name}). "
                "Модель не вернула content — попробуй Gemini Flash."
            )

    raise RuntimeError(f"OpenRouter {last_status or 'error'}: исчерпаны повторы.")


async def chat_json(**kwargs: Any) -> dict[str, Any]:
    return extract_json(await chat(as_json=True, **kwargs))


async def complete(
    *,
    model_id: str,
    messages: list[dict[str, str]],
    response_format: str | None = "carousel_v1",
    temperature: float = 0.7,
    max_tokens: int = 2800,
) -> dict[str, Any]:
    system = ""
    user_parts: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system = content if not system else f"{system}\n{content}"
        else:
            user_parts.append(content)
    user = "\n\n".join(user_parts) if user_parts else ""
    as_json = response_format is not None
    text = await chat(
        system=system or "You are a helpful assistant. Return JSON only.",
        user=user,
        as_json=as_json,
        temperature=temperature,
        max_tokens=max_tokens,
        model_id=model_id,
    )
    result: dict[str, Any] = {
        "modelId": model_id,
        "format": response_format,
        "provider": "openrouter",
    }
    if as_json:
        result["json"] = extract_json(text)
    else:
        result["text"] = text
    return result


async def health() -> dict[str, Any]:
    if not openrouter_api_key():
        return {
            "ok": False,
            "provider": "openrouter",
            "error": "OPENROUTER_API_KEY missing",
        }
    key = openrouter_api_key()
    async with httpx.AsyncClient(base_url=OPENROUTER_BASE, timeout=8.0) as client:
        try:
            resp = await client.get("/models", headers={"Authorization": f"Bearer {key}"})
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "provider": "openrouter",
                    "status": resp.status_code,
                    "error": resp.text[:200],
                }
            return {
                "ok": True,
                "provider": "openrouter",
                "models_visible": len(resp.json().get("data", [])),
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "provider": "openrouter", "error": str(exc)}
