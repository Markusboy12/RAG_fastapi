# FastAPI RAG Agent - Документация по запуску

RAG-агент по документации FastAPI с архитектурой **Simple RAG + HyDE** (Hypothetical Document Embeddings).

## 🏗️ Архитектура

```
User Query → [HyDE] → [Embed Voyage AI] → [Retrieve Qdrant] → [Grade] → [Assemble + Redis Memory] → [Generate Groq Stream] → SSE → Browser
```

### Стек технологий:
- **Backend**: FastAPI 0.115+
- **RAG Оркестрация**: LlamaIndex 0.12+
- **LLM Primary**: Groq API (qwen-3-27b)
- **LLM Fallback**: Ollama (локально)
- **Embeddings**: Voyage AI voyage-code-3
- **Vector DB**: Qdrant Cloud (hybrid search)
- **Memory**: Redis Cloud
- **Парсинг_docs**: Firecrawl API
- **Frontend**: Vanilla HTML + JS + highlight.js
- **Streaming**: Server-Sent Events (SSE)

---

## 📋 Предварительные требования

### 1. Python 3.11+
```bash
python --version  # Должно быть 3.11 или выше
```

### 2. uv (пакетный менеджер)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Или через pip:
```bash
pip install uv
```

---

## 🔑 Настройка API ключей

### 1. Скопируйте файл окружения:
```bash
cp .env.example .env
```

### 2. Получите API ключи:

#### Groq API (LLM)
1. Перейдите на https://console.groq.com
2. Зарегистрируйтесь / войдите
3. Создайте API key в разделе "API Keys"
4. Free tier: ~200 запросов/день

#### Voyage AI (Embeddings)
1. Перейдите на https://dashboard.voyageai.com
2. Зарегистрируйтесь
3. Создайте API key
4. Free tier: 200K токенов/месяц

#### Qdrant Cloud (Vector DB)
1. Перейдите на https://cloud.qdrant.io
2. Зарегистрируйтесь
3. Создайте кластер (Free tier: 1 ГБ)
4. Скопируйте URL и API key

#### Redis Cloud (Memory)
1. Перейдите на https://redis.com/try-free
2. Создайте бесплатный инстанс (30 МБ)
3. Скопируйте Redis URL

#### Firecrawl API (Парсинг документации) - опционально
1. Перейдите на https://www.firecrawl.dev
2. Зарегистрируйтесь
3. Создайте API key
4. Free tier: 500 страниц/месяц

### 3. Заполните `.env` файл:
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxx
GROQ_MODEL=qwen/qwen-3-27b

VOYAGE_API_KEY=xxxxxxxxxxxxxxxx
VOYAGE_MODEL=voyage-code-3

QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=xxxxxxxxxxxxxxxx
QDRANT_COLLECTION_NAME=fastapi_docs

REDIS_URL=redis://your-redis-url:6379
REDIS_CHAT_KEY_PREFIX=chat_memory_

FIRECRAWL_API_KEY=fc_xxxxxxxxxxxxxx

APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info
```

---

## 🚀 Установка и запуск

### 1. Установка зависимостей
```bash
cd /workspace
uv sync
```

Или через pip:
```bash
pip install -e .
```

### 2. Индексация документации FastAPI

Перед первым запуском нужно загрузить и проиндексировать документацию:

```bash
# Активация виртуального окружения
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# Запуск индексера
python -m backend.indexer
```

**Примечание:** Если Firecrawl API ключ не настроен, загрузите документы вручную:
1. Скачайте markdown файлы с https://fastapi.tiangolo.com
2. Поместите в папку `data/`
3. Модифицируйте `backend/indexer.py` для загрузки из файлов

### 3. Запуск сервера

#### Режим разработки (auto-reload):
```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Или напрямую:
```bash
python -m backend.main
```

#### Продакшен режим:
```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Открытие в браузере

Перейдите на: **http://localhost:8000**

---

## 📡 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/` | Фронтенд (Chat UI) |
| GET | `/health` | Health check |
| POST | `/chat` | Чат с SSE streaming |
| POST | `/chat/sync` | Чат JSON (fallback) |
| GET | `/api/sessions/{session_id}/history` | История сессии |
| DELETE | `/api/sessions/{session_id}` | Удаление сессии |

---

## 💬 Примеры запросов

### Через curl (streaming):
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "как сделать JWT авторизацию в FastAPI?", "session_id": "test123"}'
```

### Через curl (sync):
```bash
curl -X POST http://localhost:8000/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "что такое Dependency Injection?"}'
```

### JavaScript (fetch with streaming):
```javascript
const response = await fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: 'как создать WebSocket endpoint?',
        session_id: 'my-session'
    })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    // Парсинг SSE: data: {"token": "..."}
}
```

---

## 🧪 Тестирование

```bash
# Запуск тестов
uv run pytest tests/ -v

# Проверка кода
uv run black backend/ frontend/
```

---

## 🐳 Docker (опционально)

### Dockerfile:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
RUN uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Запуск:
```bash
docker build -t fastapi-rag-agent .
docker run -p 8000:8000 --env-file .env fastapi-rag-agent
```

---

## ☁️ Деплой на Railway / Render / Fly.io

### Railway:
1. Подключите GitHub репозиторий
2. Добавьте переменные окружения из `.env`
3. Deploy автоматически

### Render:
```yaml
# render.yaml
services:
  - type: web
    name: fastapi-rag-agent
    env: python
    buildCommand: pip install uv && uv sync
    startCommand: uv run uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - fromGroup: rag-settings
```

### Fly.io:
```bash
fly launch
fly secrets set GROQ_API_KEY=xxx VOYAGE_API_KEY=xxx ...
fly deploy
```

---

## 📊 Мониторинг и логи

### Логи приложения:
```bash
# В реальном времени
tail -f logs/app.log

# Через journalctl (systemd)
journalctl -u fastapi-rag-agent -f
```

### Health check:
```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "0.1.0"}
```

---

## 🔧 Troubleshooting

### Ошибка: "ModuleNotFoundError: No module named 'backend'"
```bash
# Убедитесь что запускаете из корня проекта
cd /workspace
export PYTHONPATH=/workspace:$PYTHONPATH
```

### Ошибка: "FIRECRAWL_API_KEY не настроен"
- Либо получите ключ на firecrawl.dev
- Либо загрузите документы вручную (см. раздел индексации)

### Ошибка: "Redis connection failed"
- Проверьте REDIS_URL в `.env`
- Убедитесь что Redis инстанс активен

### Ошибка: "Qdrant collection not found"
- Запустите индексер: `python -m backend.indexer`
- Коллекция создастся автоматически

### SSE не работает в браузере
- Проверьте консоль браузера (F12)
- Убедитесь что нет CORS ошибок
- Попробуйте `/chat/sync` endpoint

---

## 📚 Дополнительные ресурсы

- [LlamaIndex Docs](https://docs.llamaindex.ai)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Groq API Docs](https://console.groq.com/docs)
- [Voyage AI Embeddings](https://docs.voyageai.com)
- [Qdrant Hybrid Search](https://qdrant.tech/documentation/hybrid-search/)

---

## 📝 License

MIT License
