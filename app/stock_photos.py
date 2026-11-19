"""Поиск стоковых фото через Unsplash → URL (дальше resolve_cover_src → data URL)."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

import httpx

UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"
TIMEOUT = 25.0
PER_PAGE = 10


def unsplash_access_key() -> str:
    return (os.getenv("UNSPLASH_ACCESS_KEY") or "").strip()


def stock_photos_enabled() -> bool:
    flag = (os.getenv("DECKVA_STOCK_PHOTOS") or "1").strip().lower()
    if flag in {"0", "false", "off", "no"}:
        return False
    return bool(unsplash_access_key())


def _clean_query(prompt: str, *, max_words: int = 8) -> str:
    text = re.sub(r"[^\w\s\-]", " ", (prompt or "").strip(), flags=re.UNICODE)
    words = [w for w in text.split() if len(w) > 1][:max_words]
    return " ".join(words).strip() or "lifestyle editorial"


def _page_for(query: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}|{query}".encode("utf-8")).hexdigest()
    return 1 + (int(digest[:8], 16) % 5)


def _pick_index(salt: str, slide_index: int, n: int) -> int:
    if n <= 1:
        return 0
    digest = hashlib.sha256(f"{salt}|pick|{slide_index}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % n


def _orientation(orientation: str) -> str:
    if orientation in {"square", "squarish", "1:1"}:
        return "squarish"
    if orientation in {"landscape", "16:9"}:
        return "landscape"
    return "portrait"


async def _search_unsplash(
    client: httpx.AsyncClient,
    query: str,
    *,
    page: int,
    orientation: str,
) -> list[tuple[str, str]]:
    key = unsplash_access_key()
    if not key:
        return []
    resp = await client.get(
        UNSPLASH_SEARCH,
        params={
            "query": query,
            "per_page": PER_PAGE,
            "page": page,
            "orientation": _orientation(orientation),
        },
        headers={
            "Authorization": f"Client-ID {key}",
            "Accept-Version": "v1",
        },
    )
    if resp.status_code >= 400:
        return []
    data = resp.json()
    out: list[tuple[str, str]] = []
    for photo in data.get("results") or []:
        pid = str(photo.get("id") or "")
        urls = photo.get("urls") or {}
        url = str(urls.get("regular") or urls.get("full") or urls.get("small") or "").strip()
        if pid and url:
            out.append((f"unsplash:{pid}", url))
    return out


async def search_stock_photo(
    prompt: str,
    *,
    salt: str = "",
    slide_index: int = 0,
    orientation: str = "portrait",
    used_ids: set[str] | None = None,
) -> str | None:
    """
    Ищет одно фото в Unsplash по текстовому описанию.
    Возвращает https URL или None.
    """
    if not stock_photos_enabled():
        return None
    query = _clean_query(prompt)
    page = _page_for(query, f"{salt}|{slide_index}")
    used = used_ids if used_ids is not None else set()

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        try:
            hits = await _search_unsplash(
                client, query, page=page, orientation=orientation
            )
        except httpx.HTTPError:
            return None

    available = [(pid, url) for pid, url in hits if pid not in used]
    if not available:
        # fallback: другая страница без orientation
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            try:
                hits = await _search_unsplash(
                    client, query, page=max(1, page % 3 + 1), orientation="landscape"
                )
            except httpx.HTTPError:
                return None
        available = [(pid, url) for pid, url in hits if pid not in used]
    if not available:
        return None

    idx = _pick_index(salt, slide_index, len(available))
    pid, url = available[idx]
    used.add(pid)
    return url


async def fill_slide_photos_from_prompts(
    *,
    slides: list[Any],
    slide_photos: list[str],
    topic: str,
    salt: str,
    has_cover: bool,
    orientation: str = "portrait",
) -> list[str]:
    """
    Для пустых слотов с image_prompt (и cover без фото) — подтянуть Unsplash.
    Не перезаписывает уже назначенные user/attachment фото.
    """
    n = len(slides)
    photos = list(slide_photos) + [""] * max(0, n - len(slide_photos))
    photos = photos[:n]
    if not stock_photos_enabled():
        return photos

    used: set[str] = set()
    for i, slide in enumerate(slides):
        if i >= n or photos[i].strip():
            continue
        if i == n - 1:
            continue  # CTA без фото
        prompt = str(getattr(slide, "image_prompt", "") or "").strip()
        if not prompt and i == 0 and has_cover:
            prompt = f"editorial lifestyle photo {topic}"
        if not prompt:
            continue
        url = await search_stock_photo(
            prompt,
            salt=salt,
            slide_index=i,
            orientation=orientation,
            used_ids=used,
        )
        if url:
            photos[i] = url
    return photos
