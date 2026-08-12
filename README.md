# DentalAI — мультимодальный LLM-ассистент для стоматологов

Мультимодальный помощник: анализ рентгеновских снимков (vision) + RAG-чат по
клиническим протоколам с цитированием, PII-редактированием и стримингом ответов.

**Стек:**
- LLM (vision+text): **Ollama Cloud** (Gemma 4 31B) → fallback на **Gemini Flash**
- Embeddings: **Voyage AI** (`voyage-3`, 200M бесплатных токенов)
- Vector DB: **Supabase (pgvector)**, гибридный поиск из коробки
- Backend: **FastAPI + Uvicorn + Pydantic** (async, streaming, валидация JSON)
- Frontend: **Streamlit + streamlit-chat** (SSE-стриминг)
- RAG: **llama-index** (chunking), **Supabase RPC** (hybrid retrieval + metadata filter + citations)
- DICOM/Image: **pydicom + Pillow + gdcm** (windowing, preprocessing)
- PII: **Presidio** (analyzer + anonymizer) — локально, до отправки в API
- Structured Output: **instructor** (гарантированный JSON по Pydantic-схеме)
- DevOps: **GitHub Codespaces / .devcontainer**
- Config: **python-dotenv + pydantic-settings**

---

## Структура проекта

```
RAG_fastapi/
├── app/
│   ├── config.py            # настройки (pydantic-settings)
│   ├── schemas.py           # Pydantic-схемы (Findings, ChatRequest, ...)
│   ├── main.py              # FastAPI entrypoint + CORS
│   ├── api/routes.py        # /api/analyze, /api/chat (SSE)
│   ├── llm/                 # Ollama Cloud + Gemini, instructor, structured output
│   ├── rag/                 # embeddings (voyage), store (supabase), retriever, ingest
│   ├── pii/redact.py        # Presidio + зачистка PHI из DICOM
│   └── image/preprocess.py  # DICOM → windowing → PNG/base64
├── frontend/               # Streamlit UI (FDI-сетка, фильтры, чат)
├── supabase/schema.sql     # pgvector + FTS + hybrid_search()
├── .devcontainer/          # Codespaces
├── data/protocols/         # .txt клинических рекомендаций для индексации
├── requirements.txt
└── .env.example
```

MVP-функции реализованы:
1. **Мультимодальный анализ снимков** — JPEG/PNG/DICOM → windowing → Gemma 4 → `{findings:[{tooth_fdi, condition, confidence}]}`.
2. **RAG-чат с цитированием** — Hybrid Search (вектор + полнотекст) по `documents`, кликабельные ссылки на источник.
3. **Metadata filtering** — фильтры «Пациент: ребёнок/взрослый», «Раздел: эндодонтия/хирургия» передаются в retriever.
4. **Streaming** — SSE из FastAPI, посимвольный вывод в Streamlit.
5. **PII Redaction** — ФИО/даты/номера документов из текста и метаданных DICOM удаляются локально до API-вызова.
6. **Зубная формула** — визуальная сетка FDI для выбора зуба.

---

## Что нужно для запуска (по порядку)

1. **Python 3.11** (рекомендованная версия — лучшая совместимость с spacy/presidio/gdcm).
2. **Клонировать репо** и создать виртуальное окружение:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   ```
3. **Установить зависимости бэкенда:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Установить зависимости фронтенда:**
   ```bash
   pip install -r frontend/requirements.txt
   ```
5. **Скачать spaCy-модель для Presidio:**
   ```bash
   python -m spacy download en_core_web_lg
   ```
6. **Получить API-ключи** (см. ниже) и создать `.env`:
   ```bash
   cp .env.example .env   # затем заполнить значения
   ```
7. **Настроить Supabase** (см. раздел «Supabase») — выполнить `supabase/schema.sql` в SQL-редакторе.
8. **Загрузить протоколы** в `data/protocols/*.txt` и проиндексировать:
   ```bash
   python -m app.rag.ingest
   ```
9. **Запустить бэкенд:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
10. **Запустить фронтенд (второй терминал):**
    ```bash
    cd frontend && streamlit run app.py --server.port 8501
    ```
11. Открыть `http://localhost:8501`.

---

## API ключи (что нужно получить)

| Сервис | Переменная | Где взять |
|---|---|---|
| Ollama Cloud | `OLLAMA_CLOUD_API_KEY` + `OLLAMA_CLOUD_BASE_URL` | https://ollama.com/cloud (аккаунт + API key) |
| Gemini (fallback) | `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| Voyage AI | `VOYAGE_API_KEY` | https://voyageai.com (200M токенов бесплатно) |
| Supabase | `SUPABASE_URL` + `SUPABASE_KEY` | https://supabase.com → Project → Settings → API |

> Для Supabase используйте **service_role key** (или anon + отключённый RLS на таблице `documents`),
> чтобы RPC `hybrid_search` и вставка работали из бэкенда.

---

## Библиотеки и версии (стабильный набор)

Эти версии подобраны как согласованный набор, протестированный совместно:
без конфликтов зависимостей, без лагов и ошибок обработки DICOM/PII/RAG.

| Библиотека | Версия | Слой | Назначение |
|---|---|---|---|
| fastapi | 0.115.6 | Backend | API, streaming (SSE) |
| uvicorn[standard] | 0.34.0 | Backend | ASGI-сервер |
| pydantic | 2.10.4 | Backend / Frontend | валидация JSON-ответов модели |
| pydantic-settings | 2.7.0 | Backend | конфиг из `.env` |
| python-dotenv | 1.0.1 | Backend / Frontend | загрузка `.env` |
| python-multipart | 0.0.20 | Backend | загрузка файлов (снимки) |
| httpx | 0.28.1 | Backend | HTTP-клиент |
| sse-starlette | 2.2.1 | Backend | SSE-хелперы |
| numpy | 1.26.4 | Backend | обработка пикселей |
| Pillow | 11.0.0 | Backend | конвертация в PNG |
| pydicom | 2.4.4 | Backend | чтение DICOM |
| gdcm | 3.1.1 | Backend | декомпрессия DICOM |
| voyageai | 0.3.0 | Backend | embeddings (SOTA для RAG) |
| supabase | 2.10.0 | Backend | pgvector / hybrid search |
| ollama | 0.4.7 | Backend | клиент Ollama Cloud |
| google-generativeai | 0.8.4 | Backend | Gemini Flash (fallback) |
| instructor | 1.7.2 | Backend | гарантированный JSON (structured output) |
| presidio-analyzer | 2.2.359 | Backend | детекция PII |
| presidio-anonymizer | 2.2.359 | Backend | анонимизация PII |
| spacy | 3.8.0 | Backend | NLP-движок Presidio (+ модель `en_core_web_lg`) |
| llama-index-core | 0.11.23 | Backend | чанкинг документов |
| tiktoken | 0.8.0 | Backend | токенизатор для чанкера |
| streamlit | 1.41.0 | Frontend | UI |
| streamlit-chat | 0.1.1 | Frontend | чат-виджет |
| requests | 2.32.3 | Frontend | SSE-стриминг к бэкенду |

**Дополнительно (вне pip):**
- spaCy модель: `python -m spacy download en_core_web_lg` (или `en_core_web_sm` для скорости).

---

## Supabase: настройка

1. Создать проект на supabase.com.
2. В SQL Editor выполнить `supabase/schema.sql` (включает `vector`, создаёт таблицу
   `documents` и функцию `hybrid_search(query_text, query_embedding, match_count, filter)`).
3. В `embedding vector(1024)` размерность должна совпадать с `EMBED_DIM` и моделью Voyage
   (`voyage-3` → 1024). Если используете `voyage-2`, размерность та же (1024).
4. При необходимости отключить RLS для `documents` или добавить политику для service-роли.

---

## Запуск (быстрый чек-лист)

```bash
# 1. бэкенд
pip install -r requirements.txt
python -m spacy download en_core_web_lg
cp .env.example .env   # заполнить ключи
python -m app.rag.ingest   # проиндексировать протоколы
uvicorn app.main:app --port 8000 --reload

# 2. фронтенд (второй терминал)
pip install -r frontend/requirements.txt
cd frontend && streamlit run app.py --server.port 8501
```

Health-check бэкенда: `GET http://localhost:8000/health` → `{"status":"ok"}`.

---

## Примечание про стабильность версий

Набор выше проверен как цельный: `pydantic 2.10.x` + `pydantic-settings 2.7.x` и
`fastapi 0.115.x` работают без предупреждений; `presidio 2.2.359` + `spacy 3.8.0` +
`en_core_web_lg` стабильно детектят PII; `llama-index-core 0.11.x` + `tiktoken 0.8.0`
корректно чанкуют; `instructor 1.7.2` дружит с `ollama 0.4.7` и `google-generativeai 0.8.4`
для structured output. `gdcm 3.1.1` поставляется в виде готового wheel, поэтому сборка
`pydicom` не требует компиляторов. Используйте **Python 3.11** — на 3.12/3.13 возможны
проблемы со сборкой `gdcm`/`presidio` из source.
