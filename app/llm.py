"""Тонкий клиент Ollama Chat."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

OLLAMA_BASE = "http://127.0.0.1:11434"
MODEL = "qwen2.5:3b"
DEFAULT_TIMEOUT = 300.0


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


async def chat(
    *,
    system: str,
    user: str,
    as_json: bool = True,
    temperature: float = 0.85,
    top_p: float = 0.92,
    num_predict: int = 2800,
    model: str = MODEL,
    base_url: str = OLLAMA_BASE,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": num_predict,
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if as_json:
        payload["format"] = "json"

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        try:
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Ollama недоступна. Запусти `ollama serve` и модель qwen2.5:3b."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise RuntimeError("Ollama не успела ответить. Повтори запрос.") from exc

    data = resp.json()
    message = data.get("message", {}).get("content", "")
    if not isinstance(message, str) or not message.strip():
        raise RuntimeError(f"Пустой ответ Ollama: {data}")
    return message.strip()


async def chat_json(**kwargs: Any) -> dict[str, Any]:
    return extract_json(await chat(as_json=True, **kwargs))


async def health(base_url: str = OLLAMA_BASE, model: str = MODEL) -> dict[str, Any]:
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        try:
            tags = await client.get("/api/tags")
            tags.raise_for_status()
            names = [m.get("name") for m in tags.json().get("models", [])]
            return {"ok": True, "models": names, "has_model": any(model in n for n in names)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "models": [], "has_model": False}
