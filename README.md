# Deckva Carousel AI

FastAPI + Ollama `qwen2.5:3b` → Fabric JSON карусели.

Все параметры запроса обязательны. Без них — ошибка валидации / генерации.

## Запуск

```bash
ollama serve
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

## API

```json
POST /generate
{
  "topic": "как фитнес-тренеру вести блог",
  "aspect_ratio": "4:5",
  "slides_count": 7,
  "language": "ru",
  "handle": "@ekoreshilov",
  "category": "Маркетинг",
  "save": true
}
```

`aspect_ratio`: `1:1` · `4:5` · `9:16` · `16:9`
