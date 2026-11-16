# Deckva AI — CORA

FastAPI-сервис: **CORA Fast** + каталог моделей + OpenRouter gateway.

Все LLM-вызовы — только через **OpenRouter** (`OPENROUTER_API_KEY` на сервере).  
Ollama / локальные веса / BYOK **не используются**.  
Кредиты / биллинг — на **Next.js сервере**, здесь только генерация.

## Запуск

```bash
export OPENROUTER_API_KEY=sk-or-...
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Модули

| модуль | роль |
|--------|------|
| `app/llm.py` | Model Gateway → OpenRouter |
| `app/catalog.py` | каталог моделей + ACL планов |
| `app/cora/` | CORA Fast: plan → execute → assemble |
| `app/content.py` | tool `llm.fill_and_layout` |
| `app/palette.py` / `templates/` | палитра + Fabric templates (OOP registry по skillId) |
| `app/stock_photos.py` | Unsplash search по `image_prompt` |

## API

### `GET /health`
Сервис + статус OpenRouter.

### `GET /models?plan=free|pro`
Полный каталог моделей (лимит 3 бесплатных генераций на любом плане — в Next.js).

### `POST /cora/run` — единственный путь генерации
```json
{
  "userId": "u1",
  "topic": "как фитнес-тренеру вести блог",
  "language": "ru",
  "ratio": "4:5",
  "slidesCount": 7,
  "handle": "@coach",
  "cover": "",
  "mode": "fast",
  "plan": "free",
  "modelId": "gemini-flash",
  "save": false
}
```

Ответ: `coraRunId`, `CarouselPlan` с object ids, Fabric `carousel`.

### `GET /cora/runs/{coraRunId}` / `GET /cora/runs?userId=`
Статус и история run.

### `POST /internal/ai/complete`
Внутренний gateway: `{ modelId, messages, responseFormat }`.

## Env

| переменная | смысл |
|------------|--------|
| `OPENROUTER_API_KEY` | платформенный ключ (**обязателен**) |
| `DECKVA_DEFAULT_MODEL_ID` | дефолт каталога (`gemini-flash`) |
| `OPENROUTER_BASE_URL` | override API base |
| `UNSPLASH_ACCESS_KEY` | поиск обложек/фото в Unsplash (**нужен** для автофото) |
| `DECKVA_STOCK_PHOTOS` | `1`/`0` — автоподбор Unsplash по `image_prompt` (по умолчанию вкл., если есть ключ) |

### Сток-фото в карусели

CORA просит у модели `image_prompt` (english search query). Если своих картинок в `cover` / `attachments` нет и задан `UNSPLASH_ACCESS_KEY`, сервис сам ищет фото в Unsplash и вставляет на cover + 1–2 mid-слайда.

Отключить на запрос: `"stockPhotos": false` в `POST /cora/run`.
