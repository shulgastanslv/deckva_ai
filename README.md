# Deckva Carousel AI

FastAPI + Ollama `qwen2.5:3b` → Fabric JSON карусели.

Все параметры запроса обязательны (без дефолтов).

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
  "cover": "https://example.com/photo.jpg",
  "save": true
}
```

- `cover` — URL/путь картинки на 1-м слайде; `""` = серый placeholder  
  Сервер скачивает картинку и вшивает `data:` URL в JSON (без CORS в Fabric).  
- `category` — генерирует ИИ одним словом (не передавать в запросе)
