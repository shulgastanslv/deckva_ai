# Deckva Carousel AI

FastAPI + Ollama `qwen2.5:3b` → Fabric JSON карусели + AI-палитра.

Все параметры запросов обязательны (без дефолтов).

## Запуск

```bash
ollama serve
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

## Модули

| файл | роль |
|------|------|
| `app/llm.py` | тонкий клиент Ollama |
| `app/prompts.py` | системные/user промпты |
| `app/content.py` | тексты карусели и поста |
| `app/palette.py` | AI-палитра |
| `app/template.py` | Fabric-шаблоны по палитре |
| `app/generator.py` | оркестрация |

## API

### `POST /generate`

```json
{
  "topic": "как фитнес-тренеру вести блог",
  "aspect_ratio": "4:5",
  "slides_count": 7,
  "language": "ru",
  "handle": "@ekoreshilov",
  "cover": "https://example.com/photo.jpg",
  "save": true
}
```

Ответ включает `palette` и `carousel` (Fabric slides).

- `cover` — URL/путь на 1-м слайде; `""` = серый placeholder. Сервер вшивает `data:` URL.
- `category` — одно слово от ИИ (не в запросе).

### `POST /palette`

```json
{ "topic": "как фитнес-тренеру вести блог", "language": "ru" }
```

```json
{
  "name": "soft_blush",
  "bg": "#FFFFFF",
  "text": "#111111",
  "muted": "#9A9A9A",
  "accent": "#F6C1C0",
  "accent_text": "#2A2A2A",
  "grid": "#CFCFCF",
  "photo": "#C8C8C8"
}
```

### `POST /text`

```json
{ "post_text": "черновик поста..." }
```
