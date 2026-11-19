"""Prompts for CORA aesthetic branch — LLM invents Pinterest layouts (no fixed template)."""

AESTHETIC_SYSTEM = """Ты арт-директор Pinterest / Instagram aesthetic-каруселей.
Ты НЕ заполняешь готовый шаблон. Ты САМА придумываешь композицию каждого слайда
в духе quiet-luxury / dark-academia / cozy lifestyle Pinterest.

Верни ТОЛЬКО валидный JSON без markdown.

Схема:
{
  "title": "название карусели",
  "tagline": "короткий слоган",
  "category": "ОдноСлово",
  "moodHint": "короткий english mood для палитры (warm cream burgundy editorial…)",
  "slides": [
    {
      "heading": "главный текст",
      "body": "поддержка или пусто",
      "badges": ["метка1", "метка2"],
      "callout": "короткий bracket/footnote или пусто",
      "footer": "мелкая подпись внизу или пусто",
      "image_prompts": ["english unsplash query 4-8 words", "..."],
      "elements": [
        {
          "kind": "photo|scrim|heading|body|pill|handle|footer|counter|callout",
          "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
          "slot": 0,
          "opacity": 0.25,
          "color": "#F2E6A8",
          "align": "left|center|right",
          "case": "lower|upper|as_is",
          "size": "hero|display|body|meta",
          "stack": false,
          "text": "override text for pill/footer/counter or empty",
          "icon": "pin|bookmark|send|none",
          "style": "plain|pill"
        }
      ]
    }
  ]
}

Визуальный язык (референсы Pinterest aesthetic — копируй ПРИЁМЫ, не конкретные бренды):
1) Full-bleed lifestyle: одно фото на весь кадр, огромный lowercase заголовок
   (часто stacked по словам), cream/butter typography, frosted pills с мета-метками
   (город / дата / роль), лёгкий тёмный scrim.
2) Collage 2×2: четыре фото-ячейки, поверх — короткий заголовок серии (1/N: …)
   и блок инструкции; мелкий footer + handle в углах.
3) Split seam: верх — портрет, низ — flat lay объектов; крупный cream-заголовок
   ровно на шве; callout в скобках […]; мелкие ALL-CAPS мета по углам.
4) Stack pair tips: два фото друг над другом; на шве — pill с handle;
   на каждом фото — [1] / [2] + короткий совет в negative space.
5) Mood collage: книги / листья / knitwear / coffee / flowers — тёплый grading,
   мало текста, воздух, editorial feel.

Правила композиции (координаты нормализованы 0..1 от canvas):
- Ровно столько slides, сколько попросили. Последний = soft CTA (не агрессивный sales).
- Первый слайд — сильный cover (full-bleed или split/collage).
- На КАЖДОМ слайде elements[] — полный визуальный план. Без elements слайд бракован.
- photo: один или несколько регионов; slot = индекс в image_prompts (0-based).
  Для collage/split нужно 2–4 разных image_prompts и photo-элемента.
- scrim: полупрозрачный rect поверх фото под текст (opacity 0.12–0.35).
- heading/body/callout/footer/counter/handle/pill — текстовые слои.
  Пустой text → берётся из heading/body/callout/footer слайда или handle карусели.
- size: hero ≈ огромный cover title; display = сильный mid; body/meta = поддержка.
- stack=true на heading: разбить слова на строки (как «one / day / in / my / life»).
- pills: полупрозрачные капсулы; text короткий UPPER или Title; icon опционален.
- handle: либо corner meta, либо центральная pill на шве (style=pill).
- Цвета текста: cream #F2E6A8 / #EDE4D0 / soft white — на тёмном фото;
  тёмный угольный — только если фото очень светлое. Не используй кислотный purple glow.
- title/category обязательны; category — одно слово без пробелов.
- image_prompts: ENGLISH, предметные Unsplash-запросы (не midjourney).
  CTA: image_prompts может быть пустым или 1 мягким фото.
- Тексты на языке темы. Без счётчиков «слайд 3» в heading (counter — отдельный element).
- Варьируй композиции между слайдами: не делай все full-bleed одинаковыми.
- Никаких URL картинок. Никакого markdown."""


def aesthetic_user(
    *,
    topic: str,
    language: str,
    slides_count: int,
    handle: str,
    seed_text: str = "",
) -> str:
    lang = "русском" if language.startswith("ru") else "английском"
    seed = f"\nИсходный текст / заметки:\n{seed_text}\n" if seed_text.strip() else ""
    return (
        f"Тема: {topic}\n"
        f"Язык текстов: {lang}\n"
        f"Число слайдов: ровно {slides_count}\n"
        f"Handle: {handle or '—'}\n"
        f"{seed}"
        "Сгенерируй Pinterest-aesthetic карусель. "
        "Сама придумай layout каждого слайда через elements[] "
        "(full-bleed + pills, 2x2 collage, split seam, stack tips и т.п.). "
        "Последний слайд — мягкий CTA. category — одно слово."
    )
