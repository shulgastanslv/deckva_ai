"""Промпты CORA execute (fill_and_layout + palette)."""

CAROUSEL_SYSTEM = """Ты копирайтер экспертных Threads/Pinterest-каруселей.
Пиши коротко и по делу. Язык = язык темы. Если топ — составляй топ.
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

Правила структуры:
- Ровно столько slides, сколько попросили.
- layout и heading обязательны на каждом слайде.
- title и category обязательны; category — одно слово без пробелов.
- Последний слайд ВСЕГДА layout=cta.
- Первый слайд: если design.hasCover=true → layout=cover (+ image_prompt).
  Если design.hasCover=false → НЕ cover; бери statement / tips / results (текстовый hook без фото).
- Средние слайды: чередуй statement, tips, funnel, results, orange_quote — не делай все одинаковыми.
- Хотя бы один orange_quote желателен, если слайдов >= 5.
- image_prompt: короткий ENGLISH поисковый запрос для Unsplash,
  4–8 слов, предметный (people, workspace, nature, product vibe) — НЕ художественный midjourney-промпт.
  Cover: всегда заполняй image_prompt если hasCover=true.
  Средние: на 1–2 слайдах (не на всех) тоже дай image_prompt для визуального разнообразия;
  на остальных и на cta — пустая строка.
- Тексты уникальные под тему и mood.
- items без стрелок в начале.
- Без счётчиков слайдов.
- Не выдумывай URL картинок."""

PALETTE_SYSTEM = """Ты арт-директор каруселей. Каждый раз создавай СВЕЖУЮ, заметно другую палитру.
Не повторяй «белый фон + розовый акцент» — это клише. Верни ТОЛЬКО валидный JSON без markdown.

Схема:
{
  "name": "короткое_имя_латиницей",
  "bg": "#HHHHHH",
  "text": "#HHHHHH",
  "muted": "#HHHHHH",
  "accent": "#HHHHHH",
  "accent_text": "#HHHHHH",
  "grid": "#HHHHHH",
  "photo": "#HHHHHH"
}

Правила:
- Все цвета — hex #RRGGBB (6 цифр).
- Палитра ОБЯЗАНА отражать mood и тему (см. user).
- Допустимы любые режимы: light, dark, cream, saturated, muted, neo-brutal, editorial ink, candy, earth, ice, mono+1 accent.
- bg может быть тёмным, цветным, кремовым, почти чёрным — не только белым.
- text обязан читаться на bg (контраст). На тёмном bg — светлый text.
- accent — выразительный, не обязательно пастель; может быть смелым.
- accent_text — контрастен к accent (читаемый текст на accent-плашке).
- muted / grid гармоничны с bg, не «универсальный серый» каждый раз.
- photo — тон подложки фото-зоны, согласованный с палитрой.
- name отражает характер (например midnight_ink, butter_pop, moss_editorial)."""


def carousel_user(
    *,
    topic: str,
    language: str,
    slides_count: int,
    handle: str,
    plan_briefs: str = "",
    has_cover: bool = True,
    mood: str = "",
    skill_brief: str = "",
) -> str:
    lang = "русском" if language.startswith("ru") else "английском"
    extra = f"\nПлан объектов (briefs):\n{plan_briefs}\n" if plan_briefs else ""
    cover_line = (
        "Первый слайд: layout=cover, добавь image_prompt (english stock search query)."
        if has_cover
        else "Первый слайд: БЕЗ cover — layout=statement (или tips/results), image_prompt пустой."
    )
    mood_line = f"Mood / тон визуала: {mood}\n" if mood else ""
    skill_line = f"Skill / структура карусели: {skill_brief}\n" if skill_brief.strip() else ""
    return (
        f"Тема: {topic}\n"
        f"Язык: {lang}\n"
        f"Число слайдов: ровно {slides_count}\n"
        f"Хэндл (контекст): {handle}\n"
        f"{mood_line}"
        f"{skill_line}"
        f"design.hasCover={str(has_cover).lower()}\n"
        f"{cover_line}\n"
        f"{extra}"
        "Сгенерируй карусель. category — одно слово. "
        "Если задан skill — строго следуй его структуре ролей. "
        "Варьируй layout средних слайдов. Последний layout=cta. "
        "На 1–2 средних слайдах добавь image_prompt для стокового фото; на остальных — пусто."
    )

def carousel_extra_user(
    *,
    topic: str,
    language: str,
    count: int,
    handle: str,
    existing_headings: list[str],
) -> str:
    lang = "русском" if language.startswith("ru") else "английском"
    used = "\n".join(f"- {h}" for h in existing_headings[:12])
    return (
        f"Тема: {topic}\n"
        f"Язык: {lang}\n"
        f"Нужно ещё ровно {count} слайд(ов).\n"
        f"Хэндл: {handle}\n"
        f"Уже есть заголовки (не повторяй):\n{used}\n"
        'Верни JSON: {"slides":[...]} с layout и heading. '
        "Не используй layout=cover или layout=cta — только средние: "
        "statement|orange_quote|tips|funnel|results."
    )


def palette_user(*, topic: str, language: str, mood: str = "") -> str:
    lang = "русском" if language.startswith("ru") else "английском"
    mood_line = f"Обязательный mood: {mood}\n" if mood else ""
    return (
        f"Тема карусели: {topic}\n"
        f"Язык контекста: {lang}\n"
        f"{mood_line}"
        "Подбери смелую, запоминающуюся палитру под эту тему. "
        "Избегай дефолтного белого + пыльно-розового."
    )
