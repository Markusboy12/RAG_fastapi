# 🚀 КРАТКАЯ ИНСТРУКЦИЯ ПО ЗАПУСКУ

## 1. Настройка API ключей

```bash
# Скопируйте шаблон .env
cp .env.example .env

# Отредактируйте .env и заполните ключами:
nano .env  # или ваш любимый редактор
```

### Необходимые ключи (получить бесплатно):
- **GROQ_API_KEY**: https://console.groq.com
- **VOYAGE_API_KEY**: https://dashboard.voyageai.com  
- **QDRANT_URL** + **QDRANT_API_KEY**: https://cloud.qdrant.io
- **REDIS_URL**: https://redis.com/try-free
- **FIRECRAWL_API_KEY** (опционально): https://www.firecrawl.dev

---

## 2. Быстрый старт

```bash
# Установка зависимостей
uv sync

# Индексация документации (требуется FIRECRAWL_API_KEY)
python -m backend.indexer

# Запуск сервера
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Или используйте скрипт:
```bash
./scripts/run.sh
```

---

## 3. Открыть в браузере

**http://localhost:8000**

---

## 4. Проверка работы API

```bash
# Health check
curl http://localhost:8000/health

# Тестовый запрос (sync)
curl -X POST http://localhost:8000/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"message": "как сделать JWT авторизацию в FastAPI?"}'
```

---

## 📁 Структура проекта

```
/workspace/
├── backend/
│   ├── __init__.py
│   ├── config.py        # Настройки приложения
│   ├── indexer.py       # Загрузка и индексация docs
│   ├── pipeline.py      # RAG пайплайн с HyDE
│   └── main.py          # FastAPI сервер
├── frontend/
│   ├── index.html       # Chat UI
│   ├── styles.css       # Стили
│   └── app.js           # SSE streaming клиент
├── scripts/
│   └── run.sh           # Скрипт запуска
├── pyproject.toml       # Зависимости
├── .env.example         # Шаблон переменных
└── README_RUN.md        # Полная документация
```

---

## 🔧 Если что-то не работает

1. **Python 3.11+?** → `python --version`
2. **Зависимости установлены?** → `uv sync`
3. **API ключи в .env?** → Проверьте `.env`
4. **Документация проиндексирована?** → `python -m backend.indexer`

Полная документация: **README_RUN.md**
