from __future__ import annotations

import json
import re
from typing import Any

import httpx

OLLAMA_BASE = "http://127.0.0.1:11434"
MODEL = "qwen2.5:3b"


SYSTEM_PROMPT = """Ты копирайтер экспертных Threads/Pinterest-каруселей.
Пиши коротко и по делу. Язык = язык темы. Если топ = составляй топ.
Верни ТОЛЬКО валидный JSON без markdown.

Схема:
{
  "title": "название карусели",
  "tagline": "слоган блога",
  "category": "ОдноСлово",
  "slides": [
    {
      "layout": "cover|statement|orange_quote|tips|funnel|results|cta",
      "heading": "заголовок",
      "highlight": "фраза из heading или пустая строка",
      "body": "подзаголовок или абзац или пустая строка",
      "items": ["пункт"],
      "badges": [],
      "flow": "",
      "callout": "",
      "tag": "",
      "image_prompt": "english lifestyle photo description или пустая строка"
    }
  ]
}

Структура:
1) первый слайд — layout cover (heading + body, image_prompt)
2…) statement / tips / funnel / results / orange_quote
последний) layout cta

Правила:
- Ровно столько slides, сколько попросили.
- layout обязателен у каждого слайда.
- heading обязателен и непустой.
- title обязателен.
- category обязателен: ровно ОДНО слово (без пробелов), по теме карусели.
- Все тексты уникальные под тему.
- items без стрелок в начале.
- Не пиши счётчики слайдов."""

POST_TEXT_SYSTEM_PROMPT = """
Роль: Ты опытный копирайтер, специализирующийся на вирусном контенте для Threads и Pinterest-каруселей. Твоя цель — превратить исходный текст в вовлекающий, легко читаемый пост, который цепляет с первой строки и стимулирует пользователей оставлять комментарии или сохранять пост.

Контекст:
- Исходный материал: {post_text}
- Платформа: Threads / Pinterest
- Целевая аудитория: эксперты, предприниматели, люди, интересующиеся саморазвитием, бизнесом и трендами.

Правила и структура поста:
1. Крючок (Hook): Первая строка должна вызывать сильный интерес, интригу или затрагивать боль читателя, чтобы он нажал кнопку «Ещё». Без скучных приветствий.
2. Тело поста (Body): 
   - Излагай мысли тезисно, используя короткие абзацы (не более 2–3 строк).
   - Применяй списки с маркерами или эмодзи для улучшения читаемости.
   - Убери «воду», канцелярит и сложные конструкции. Пиши живым, разговорным, но экспертным языком.
3. Интерактив / Призыв к действию (CTA): В конце поста задай вовлекающий вопрос аудитории или предложи поделиться мнением, чтобы спровоцировать дискуссию в комментариях.
4. Ограничения: 
   - Не используй избыток хештегов (для Threads достаточно 1-2 тематических или вообще без них).
   - Общая длина текста должна быть комфортной для чтения в ленте (в пределах лимита символов Threads).

Формат ответа:
Верни ТОЛЬКО готовый текст поста, без вводных фраз, пояснений и комментариев с твоей стороны.

"""

def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def generate_post_text_content(post_text: str) -> str:
    if not post_text.strip():
        raise RuntimeError("Не указан post_text.")

    payload = {
        "model": "qwen2.5:3b",
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.85, "top_p": 0.92, "num_predict": 2800},
        "messages": [
            {"role": "system", "content": POST_TEXT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Текст поста: {post_text}"},
        ],
    }

    async with httpx.AsyncClient(base_url=OLLAMA_BASE, timeout=300.0) as client:
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
    if not message:
        raise RuntimeError(f"Пустой ответ Ollama: {data}")
    return message


async def generate_content(
    topic: str,
    *,
    slides_count: int,
    language: str,
    handle: str,
    base_url: str = OLLAMA_BASE,
    model: str = MODEL,
    timeout: float = 300.0,
) -> dict[str, Any]:
    if not topic.strip():
        raise RuntimeError("Не указан topic.")
    if not handle.strip():
        raise RuntimeError("Не указан handle.")
    if not language.strip():
        raise RuntimeError("Не указан language.")
    if slides_count < 4:
        raise RuntimeError("slides_count должен быть >= 4.")

    lang = "русском" if language.startswith("ru") else "английском"
    user = (
        f"Тема: {topic}\n"
        f"Язык: {lang}\n"
        f"Число слайдов: ровно {slides_count}\n"
        f"Хэндл (для контекста): {handle}\n"
        "Сгенерируй полную карусель: все тексты уникальные.\n"
        "Обязательно верни category — одно слово по теме.\n"
        "Первый layout=cover, последний layout=cta."
    )

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.85, "top_p": 0.92, "num_predict": 2800},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        try:
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Ollama недоступна. Запусти `ollama serve` и модель qwen2.5:3b."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise RuntimeError(
                "Ollama не успела ответить. Повтори или уменьши slides_count."
            ) from exc
        data = resp.json()

    message = data.get("message", {}).get("content", "")
    if not message:
        raise RuntimeError(f"Пустой ответ Ollama: {data}")
    return _extract_json(message)


async def generate_extra_slides(
    topic: str,
    *,
    count: int,
    language: str,
    existing_headings: list[str],
    handle: str,
    base_url: str = OLLAMA_BASE,
    model: str = MODEL,
    timeout: float = 300.0,
) -> dict[str, Any]:
    if count < 1:
        raise RuntimeError("count для догенерации должен быть >= 1.")
    if not handle.strip():
        raise RuntimeError("Для догенерации нужен handle.")

    lang = "русском" if language.startswith("ru") else "английском"
    used = "\n".join(f"- {h}" for h in existing_headings[:12])
    if not used:
        raise RuntimeError("Нет существующих заголовков для догенерации.")

    user = (
        f"Тема: {topic}\n"
        f"Язык: {lang}\n"
        f"Нужно ещё ровно {count} слайд(ов).\n"
        f"Хэндл: {handle}\n"
        f"Уже есть заголовки (не повторяй):\n{used}\n"
        'Верни JSON: {"slides":[...]} с обязательными layout и heading.'
    )
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.9, "top_p": 0.92, "num_predict": 1600},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        try:
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "Ollama недоступна. Запусти `ollama serve` и модель qwen2.5:3b."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise RuntimeError("Ollama не успела ответить при догенерации слайдов.") from exc
        data = resp.json()
    message = data.get("message", {}).get("content", "")
    if not message:
        raise RuntimeError(f"Пустой ответ Ollama при догенерации: {data}")
    return _extract_json(message)


async def health(base_url: str = OLLAMA_BASE, model: str = MODEL) -> dict[str, Any]:
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        try:
            tags = await client.get("/api/tags")
            tags.raise_for_status()
            names = [m.get("name") for m in tags.json().get("models", [])]
            return {"ok": True, "models": names, "has_model": any(model in n for n in names)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "models": [], "has_model": False}
