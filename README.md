# FastAPI RAG Agent with HyDE

Интеллектуальный RAG-агент для работы с документацией FastAPI, использующий архитектуру **Simple RAG + HyDE** (Hypothetical Document Embeddings) для повышения точности поиска кода и примеров.

## 🚀 Особенности

- **HyDE (Hypothetical Document Embeddings)**: Генерация гипотетического кода перед поиском для улучшения релевантности
- **Hybrid Search**: Комбинация векторного и keyword поиска в Qdrant
- **Streaming Responses**: Потоковая передача токенов через Server-Sent Events (SSE)
- **Memory**: История диалога в Redis для контекстных ответов
- **Code Highlighting**: Подсветка синтаксиса Python/FastAPI на фронтенде
- **Fallback LLM**: Автоматическое переключение на Ollama при ошибках Groq
- **Free Tier Ready**: Все сервисы работают на бесплатных тарифах

## 🏗️ Архитектура

```
User Query → HyDE (Groq) → Voyage AI Embeddings → Qdrant Hybrid Search 
           → Grade → Redis Memory → Groq Streaming → SSE → Browser
```

### Компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **LLM (Primary)** | Groq API (Qwen-2.5-Coder-32B) | Генерация HyDE запросов и ответов |
| **LLM (Fallback)** | Ollama Cloud | Резервный LLM при ошибках Groq |
| **Embeddings** | Voyage AI (voyage-code-3) | Векторизация кода и документации |
| **Vector DB** | Qdrant Cloud | Hybrid search (vector + keyword) |
| **Memory** | Redis Cloud | История сообщений + кэш эмбеддингов |
| **Parser** | Firecrawl API | Извлечение docs.fastapi.dev → Markdown |
| **Backend** | FastAPI 0.115+ | REST API + SSE streaming |
| **Frontend** | Vanilla HTML/JS | Chat UI + highlight.js |
| **RAG Orchestrator** | LlamaIndex 0.12+ | Чанкинг, HyDE, retrieval, memory |

## 📋 Требования

- Python 3.11+
- uv или poetry (рекомендуется uv)
- Docker (опционально, для локального Redis/Qdrant)

## 🔑 Необходимые API ключи

Получите бесплатные ключи для следующих сервисов:

| Сервис | URL | Лимиты Free Tier |
|--------|-----|------------------|
| **Groq** | https://console.groq.com | ~30 req/min |
| **Voyage AI** | https://dashboard.voyageai.com | 200M токенов/мес |
| **Qdrant** | https://cloud.qdrant.io | 1 ГБ хранилища |
| **Redis** | https://redis.com/try-free | 30 МБ |
| **Firecrawl** | https://www.firecrawl.dev | 500 страниц/мес |

## ⚙️ Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd fastapi-rag-agent
```

### 2. Настройка переменных окружения

Скопируйте шаблон `.env.example` в `.env` и заполните ключами:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# LLM
GROQ_API_KEY=gsk_...
OLLAMA_BASE_URL=http://localhost:11434  # опционально

# Embeddings
VOYAGE_API_KEY=...

# Vector DB
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=fastapi_docs

# Memory & Cache
REDIS_URL=rediss://default:password@host:6379

# Parser
FIRECRAWL_API_KEY=fc_...  # опционально, можно использовать прямой парсинг

# App Settings
LOG_LEVEL=INFO
MAX_MEMORY_MESSAGES=5
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
```

### 3. Установка зависимостей

Рекомендуется использовать **uv** для быстрой установки:

```bash
# Установка uv (если не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Синхронизация зависимостей
uv sync
```

Или через pip:

```bash
pip install -r requirements.txt
```

## 🚀 Запуск

### Шаг 1: Индексация документации

Загрузите документацию FastAPI в векторную базу данных:

```bash
uv run python -m backend.indexer
```

Процесс:
1. Firecrawl извлекает страницы с `docs.fastapi.dev`
2. LlamaIndex разбивает на чанки (512 токенов, overlap 50)
3. Voyage AI генерирует эмбеддинги
4. Чанки сохраняются в Qdrant с метаданными

⏱️ Время выполнения: ~5-10 минут

### Шаг 2: Запуск сервера

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Или используйте скрипт:

```bash
./scripts/run.sh
```

### Шаг 3: Открытие интерфейса

Перейдите в браузере: **http://localhost:8000**

## 📡 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/` | Статический фронтенд (Chat UI) |
| `POST` | `/chat` | SSE streaming ответ |
| `POST` | `/chat/sync` | JSON ответ (fallback) |
| `GET` | `/health` | Проверка работоспособности |
| `POST` | `/index/rebuild` | Пересоздать индекс документов |

### Пример запроса через curl

```bash
# Streaming запрос
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "как сделать JWT авторизацию в FastAPI?"}'
```

## 💬 Примеры запросов

Попробуйте задать агенту следующие вопросы:

- *"Как создать endpoint с OAuth2PasswordBearer?"*
- *"Покажи пример зависимости для проверки JWT токена"*
- *"Как валидировать request body с помощью Pydantic?"*
- *"Объясни разницу между Depends и Security"*
- *"Как настроить CORS middleware?"*

## 🧪 Тестирование

Запуск тестов (если добавлены):

```bash
uv run pytest tests/ -v
```

## 🐳 Docker (опционально)

Для локального запуска Redis и Qdrant:

```bash
docker-compose up -d
```

Обновите `.env` для использования локальных сервисов:

```env
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

## 📁 Структура проекта

```
fastapi-rag-agent/
├── backend/
│   ├── __init__.py
│   ├── config.py          # Настройки и env variables
│   ├── indexer.py         # Загрузка и индексация документов
│   ├── pipeline.py        # RAG пайплайн (HyDE, retrieval, memory)
│   └── main.py            # FastAPI сервер + endpoints
├── frontend/
│   ├── index.html         # Chat UI
│   ├── styles.css         # Стили
│   └── app.js             # SSE клиент + highlight.js
├── scripts/
│   └── run.sh             # Скрипт запуска
├── tests/                 # Тесты (опционально)
├── pyproject.toml         # Зависимости
├── .env.example           # Шаблон переменных окружения
├── .gitignore
└── README.md              # Этот файл
```

## 🔧 Настройка параметров

В `.env` можно настроить:

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `CHUNK_SIZE` | 512 | Размер чанка в токенах |
| `CHUNK_OVERLAP` | 50 | Перекрытие между чанками |
| `TOP_K_RESULTS` | 5 | Количество результатов поиска |
| `MAX_MEMORY_MESSAGES` | 5 | Сообщений истории в Redis |
| `HYDE_MODEL` | qwen-2.5-coder-32b | Модель для HyDE |
| `RESPONSE_MODEL` | qwen-2.5-coder-32b | Модель для генерации ответа |

## 🛠️ Troubleshooting

### Ошибка подключения к Qdrant
- Проверьте `QDRANT_URL` и `QDRANT_API_KEY`
- Убедитесь, что коллекция создана (`indexer.py` создаёт автоматически)

### Ошибка Groq API
- Проверьте лимиты rate limiting (~30 req/min на free tier)
- При частых ошибках включите fallback на Ollama

### Медленная индексация
- Уменьшите `CHUNK_SIZE` или параллелизуйте загрузку
- Firecrawl free tier: 500 страниц/мес

### Пустые ответы
- Проверьте, что индексация завершена успешно
- Увеличьте `TOP_K_RESULTS` до 10

## 📊 Мониторинг

Логирование настроено через стандартный `logging` модуль Python.

Уровень логирования: `LOG_LEVEL=INFO` (можно изменить на `DEBUG`)

Ключевые метрики для отслеживания:
- Время ответа (time to first token)
- Количество чанков в контексте
- Score релевантности搜索结果

## 🤝 Contributing

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License

## 🔗 Полезные ссылки

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [LlamaIndex Docs](https://docs.llamaindex.ai)
- [HyDE Paper](https://arxiv.org/abs/2212.10496)
- [Qdrant Documentation](https://qdrant.tech/documentation)
- [Groq Cloud](https://console.groq.com)
- [Voyage AI Embeddings](https://docs.voyageai.com/docs/embeddings)

---

**Сделано с ❤️ для сообщества FastAPI**