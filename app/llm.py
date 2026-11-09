"""Model Gateway: Deckva modelId → OpenRouter. Без Ollama / BYOK / локальных весов."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.catalog import get_model

OPENROUTER_BASE = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
DEFAULT_TIMEOUT = float(os.getenv("OPENROUTER_TIMEOUT", "180"))
DEFAULT_MODEL_ID = os.getenv("DECKVA_DEFAULT_MODEL_ID", "gemini-flash")


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


async def chat(
    *,
    system: str,
    user: str,
    as_json: bool = True,
    temperature: float = 0.85,
    top_p: float = 0.92,
    max_tokens: int = 2800,
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

    async with httpx.AsyncClient(base_url=OPENROUTER_BASE, timeout=timeout) as client:
        try:
            resp = await client.post("/chat/completions", json=payload, headers=headers)
        except httpx.ConnectError as exc:
            raise RuntimeError("OpenRouter недоступен (connect error).") from exc
        except httpx.ReadTimeout as exc:
            raise RuntimeError("OpenRouter не успел ответить. Повтори запрос.") from exc

    if resp.status_code == 429:
        raise RuntimeError("OpenRouter 429: rate limit. Повтори позже.")
    if resp.status_code >= 500:
        raise RuntimeError(f"OpenRouter {resp.status_code}: upstream error.")
    if resp.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter {resp.status_code} ({resolved_id}/{slug}): {resp.text[:300]}"
        )

    data = resp.json()
    try:
        message = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Пустой/битый ответ OpenRouter: {data}") from exc
    if not isinstance(message, str) or not message.strip():
        raise RuntimeError(f"Пустой ответ OpenRouter: {data}")
    return message.strip()


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
