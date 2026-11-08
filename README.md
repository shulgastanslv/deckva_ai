# Deckva AI — CORA

FastAPI-сервис: **CORA Fast** + кредитный хаб + каталог моделей через **один** `OPENROUTER_API_KEY`.

Ollama / локальные веса / BYOK **не используются**.

Спеки: `cora-system.md`, `credits-models-hub.md` (Phase A, минимальный объём).

## Запуск

```bash
export OPENROUTER_API_KEY=sk-or-...
python -m venv .venv && source .venv/bin/activate  # или Windows activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Что внутри (MVP)

| модуль | роль |
|--------|------|
| `app/llm.py` | Model Gateway → OpenRouter |
| `app/catalog.py` | `AiModelCatalog` + ACL планов |
| `app/credits.py` | quote → hold → spend / refund (in-memory) |
| `app/cora/` | CORA Fast: plan → execute → assemble |
| `app/content.py` / `palette.py` / `template.py` | fill + Fabric assemble |

Free-кошелёк сидится **150 promo-кредитами** (~3 Economy-генерации).

## API

### `GET /health`
Проверка сервиса + OpenRouter.

### `GET /models?plan=free|starter|pro`
Каталог моделей, доступных плану (Free = только Economy).

### `POST /credits/quote`
```json
{
  "userId": "u1",
  "modelId": "gemini-flash",
  "slides": 7,
  "mode": "fast",
  "plan": "free"
}
```

### `GET /credits/wallet/{userId}?plan=free`
Баланс buckets + ledger.

### `POST /cora/run` — основной путь
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

Ответ: `coraRunId`, сохранённый `CarouselPlan` с object ids, Fabric `carousel`, `credits` (quoted/spent/holdId). При ошибке upstream — **refund hold**.

### `POST /internal/ai/complete`
Внутренний gateway: `{ modelId, messages, responseFormat }`.

### Legacy
`POST /generate`, `/palette`, `/text` — те же генерации через OpenRouter (без кредитного обёртывания).

## Env

| переменная | смысл |
|------------|--------|
| `OPENROUTER_API_KEY` | платформенный ключ (обязателен) |
| `DECKVA_DEFAULT_MODEL_ID` | дефолт, если modelId не передан (`gemini-flash`) |
| `OPENROUTER_BASE_URL` | override API base |
