"""Скачивание обложки на сервере → data URL (без CORS в Fabric/браузере)."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import httpx

MAX_BYTES = 8 * 1024 * 1024  # 8 MB


def _guess_mime(url: str, content_type: str | None) -> str:
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct.startswith("image/"):
            return ct
    path = urlparse(url).path
    guessed, _ = mimetypes.guess_type(path)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


async def resolve_cover_src(cover: str) -> str:
    """
    Пустая строка → "".
    data: → как есть.
    http(s) / локальный файл → data:<mime>;base64,...
    """
    cover = (cover or "").strip()
    if not cover:
        return ""
    if cover.startswith("data:image/"):
        return cover

    # локальный путь
    local = Path(cover)
    if local.is_file():
        data = local.read_bytes()
        if len(data) > MAX_BYTES:
            raise RuntimeError("Файл cover слишком большой (макс. 8MB).")
        mime = _guess_mime(cover, None)
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    if not (cover.startswith("http://") or cover.startswith("https://")):
        raise RuntimeError("cover должен быть URL (http/https), data: или путём к файлу.")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DeckvaCarousel/1.0)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True, headers=headers) as client:
        try:
            resp = await client.get(cover)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Не удалось скачать cover: {exc}") from exc

    data = resp.content
    if not data:
        raise RuntimeError("Cover URL вернул пустое тело.")
    if len(data) > MAX_BYTES:
        raise RuntimeError("Cover слишком большой (макс. 8MB).")

    mime = _guess_mime(cover, resp.headers.get("content-type"))
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
