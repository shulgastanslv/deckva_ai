# Deckva AI — CORA

FastAPI-сервис: **CORA Fast** + кредитный хаб + каталог моделей.

Все LLM-вызовы — только через **OpenRouter** (`OPENROUTER_API_KEY` на сервере).  
Ollama / локальные веса / BYOK **не используются**.

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
| `app/credits.py` | quote → hold → spend / refund |
| `app/cora/` | CORA Fast: plan → execute → assemble |
| `app/content.py` | tool `llm.fill_and_layout` |
| `app/palette.py` / `template.py` | палитра + Fabric assemble |

Free-кошелёк: **150 promo-кредитов** (~3 Economy-генерации).

## API

### `GET /health`
Сервис + статус OpenRouter.

### `GET /models?plan=free|starter|pro`
Каталог моделей плана (Free = Economy).

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

### `GET /credits/wallet/{userId}`
Баланс buckets + ledger.

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

Ответ: `coraRunId`, `CarouselPlan` с object ids, Fabric `carousel`, `credits`.  
При ошибке upstream — **refund hold**.

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
