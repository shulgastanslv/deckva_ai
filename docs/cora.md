# CORA — как работает генерация карусели

**CORA Fast** = один запрос → готовая Fabric-карусель.  
Все LLM-вызовы идут через **OpenRouter**. Биллинг снаружи (Next.js).

Точка входа: `POST /cora/run` → `run_cora_fast()`.

---

## Большая картина

```mermaid
flowchart LR
  A[Запрос] --> B[Intake]
  B --> C[Plan]
  C --> D[Execute]
  D --> E[Assemble]
  E --> F[Карусель JSON]
```

| Фаза | Что делает | LLM? |
|------|------------|------|
| **Intake** | Читает тему, фото, skill, handle | нет |
| **Plan** | Решает структуру слайдов и mood | нет (рандом от runId) |
| **Execute** | Пишет тексты, палитру, шрифт; ищет фото | да |
| **Assemble** | Собирает Fabric-слайды по шаблону skill | нет |

Статусы run: `planning` → `executing` → `assembling` → `done` / `failed`.

---

## 1. Intake — что пришло

Из запроса берём:

- тему, язык, ratio, число слайдов (1–10)
- `handle` + флаг `showHandle`
- обложку / картинки / текстовые заметки
- опционально `skillId`, `font`, `brandKit`, `stockPhotos`

```mermaid
flowchart TD
  R[CoraRunRequest] --> I[Картинки → data URL]
  R --> S[Тексты → seed]
  R --> K[skillId]
  I --> D{Есть фото?}
  D -->|да| FC[forceCover = true]
  D -->|нет| NC[cover решает Plan]
```

- Картинки: cover / attachments → нормализуются в data URL.
- Тексты: `seedText` + text-attachments → один seed для копирайтера.
- Если есть любое фото или cover — обложка **обязательна**.

---

## 2. Plan — скелет карусели

Планировщик **не зовёт LLM**. Выбор детерминирован от `coraRunId + topic`.

### 2.1. Design

```mermaid
flowchart TD
  RNG[RNG от runId+topic] --> M[mood]
  RNG --> C{hasCover?}
  RNG --> G[gridMode]
  RNG --> R[роли mid-слайдов]
  RNG --> L[layouts mid-слайдов]
  M --> DES[design]
  C --> DES
  G --> DES
  R --> DES
  L --> DES
  SK[skillId?] -->|да| OVR[перезаписывает роли/cover/brief]
  OVR --> DES
```

В `design` попадает:

- `hasCover`, `mood`, `gridMode`, `accentBias`, `photoRatio`
- `midRoles` / `midLayouts` — что делают средние слайды
- если задан **skill** — жёсткая структура (howto, myths, pricing…)

### 2.2. Skeleton plan

На каждый слайд создаются объекты с **стабильными id**:

```
s0_headline, s0_body, s0_cover?
s1_headline, s1_body
…
sN_headline, sN_body   ← последний = CTA
```

```mermaid
flowchart LR
  subgraph slide0 [Слайд 0]
    H0[headline]
    B0[body]
    C0[cover?]
  end
  subgraph mid [Средние]
    Hi[headline]
    Bi[body]
  end
  subgraph last [Последний]
    Hn[headline]
    Bn[cta]
  end
  slide0 --> mid --> last
```

План = карта «какие слоты заполнить». Тексты пока пустые.

---

## 3. Execute — контент и визуал

Здесь работают модели.

```mermaid
sequenceDiagram
  participant C as CORA
  participant L as OpenRouter
  participant U as Unsplash

  C->>L: fill_and_layout (тексты + layouts + image_prompt)
  L-->>C: raw JSON карусели
  C->>C: normalize_slides (добить/починить число и layouts)
  opt stockPhotos и нет своих фото
    C->>U: поиск по image_prompt
    U-->>C: URL → data URL
  end
  C->>L: generate_palette (цвета под mood)
  L-->>C: palette
  C->>L: generate_typography (шрифт + размеры ≤ 70)
  L-->>C: typography
```

### Тексты

1. В topic подмешиваются skill-brief и seed.
2. LLM возвращает `title`, `category`, `slides[]` (`layout`, `heading`, `body`, `items`, `image_prompt`…).
3. `normalize_slides` гарантирует:
   - ровно N слайдов
   - первый = cover (если `hasCover`) иначе не-cover
   - последний = `cta`
   - средние без случайного cover/cta

### Фото

Порядок приоритета:

1. Свои картинки пользователя  
2. Unsplash по `image_prompt` (если `stockPhotos=true` и есть ключ)  
3. Пусто → placeholder / текстовый слайд

Раскладка: `[0]` = cover, дальше mid-слайды, **CTA без фото**.

### Палитра и шрифт

- Палитра — свежие hex под topic + mood.
- Шрифт — из каталога `/fonts` (кириллица + латиница).
- Размер заголовка ограничен **70**.
- `showHandle=false` → хэндл не рисуется.

---

## 4. Assemble — Fabric JSON

```mermaid
flowchart TD
  BIND[bind_content_to_plan<br/>value в object ids]
  TPL[Шаблон по skillId<br/>или default]
  LAY[layout_cover / content / quote / cta]
  STAMP[coraObjectId на Textbox/Image]
  BIND --> TPL --> LAY --> STAMP --> OUT[carousel.slides]
```

1. Тексты из slides прописываются в plan-objects (`value`).
2. Берётся визуальный шаблон (`skillId` → registry, иначе default).
3. Каждый слайд собирается в Fabric-объекты (rect, textbox, image) с палитрой и типографикой.
4. На слои ставится `coraObjectId` = id из плана (`s0_headline` …) — чтобы клиент мог править объект точечно.
5. Опционально `save=true` → файл в `output/`.

Ответ API: `plan` + `objectBindings` + `palette` + `carousel`.

---

## Поток данных одной строкой

```text
тема + skill + фото
    → design (mood, cover, роли)
    → plan (слоты s*_headline / s*_body)
    → LLM тексты
    → фото (свои / Unsplash)
    → LLM палитра + шрифт
    → Fabric slides + coraObjectId
```

---

## Skills

`skillId` фиксирует **смысловую** структуру mid-слайдов и brief для копирайтера.

Примеры: `launch`, `howto`, `tips`, `myths`, `pricing`, `aesthetic`, `lookbook`…

Без skill — CORA сама кидает роли из пулов (hook / offer / proof / …).

### Skill `aesthetic`

Как остальные skills: LLM пишет только тексты (`fill_and_layout`), геометрия — в
`AestheticTemplate` (`app/templates/aesthetic.py`).

Два ровных варианта по референсам (цикл mid + cover от runId):

- `portrait` — full-bleed фото, одинаковые отступы: top-left tagline, top-right `@handle`,
  на cover — прямой центрированный заголовок + `/callout/`, на mid — left caption (2 строки)
- `collage` — равный 2×2 grid, чёрная скруглённая плашка по центру, footer tag + `@handle`
- CTA: `cta_soft`

Mood: `pinterest_editorial`. `collage` берёт 4 фото-слота
(`design.slidePhotoSets`) через Unsplash.

Шрифты только из 5: Poppins, Montserrat, Manrope, Raleway, Ubuntu
(`AESTHETIC_FONT_CATALOG` в `app/fonts.py`).

---

## Что где в коде

| Кусок | Файл |
|-------|------|
| Оркестратор | `app/cora/runner.py` |
| Design + skeleton plan | `app/cora/plan.py` |
| Skills | `app/cora/skills.py` |
| Тексты LLM | `app/content.py` + `app/prompts.py` |
| Aesthetic layouts | `app/templates/aesthetic.py` (`portrait` / `collage`) |
| Aesthetic multi-slot photos | `app/cora/aesthetic/photos.py` |
| Палитра | `app/palette.py` |
| Шрифты | `app/fonts.py` |
| Сборка Fabric | `app/cora/assemble.py` + `app/templates/` |
| Сток-фото | `app/stock_photos.py` |

---

## Коротко

CORA сначала **жёстко планирует каркас** (без LLM), потом **трижды зовёт модель** (тексты → цвета → шрифт), подкладывает фото и **собирает** готовые слайды так, чтобы каждый текст имел стабильный object id.
