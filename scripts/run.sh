#!/usr/bin/env bash
# Скрипт для быстрой установки и запуска FastAPI RAG Agent

set -e

echo "🚀 FastAPI RAG Agent - Установка и запуск"
echo "=========================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION найден"

# Проверка/установка uv
if ! command -v uv &> /dev/null; then
    echo "⏳ Установка uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ uv найден"

# Создание .env если не существует
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Копируем из .env.example..."
    cp .env.example .env
    echo "❗ Заполните .env файлик вашими API ключами!"
    echo "   Необходимые ключи: GROQ_API_KEY, VOYAGE_API_KEY, QDRANT_URL, QDRANT_API_KEY, REDIS_URL"
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Установка зависимостей
echo "⏳ Установка зависимостей..."
uv sync

# Индексация документации
echo ""
echo "📚 Индексация документации FastAPI..."
echo "⚠️  Для индексации требуется FIRECRAWL_API_KEY в .env"
read -p "Запустить индексацию сейчас? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    uv run python -m backend.indexer
fi

# Запуск сервера
echo ""
echo "🎉 Запуск сервера..."
echo "=========================================="
echo "Откройте браузер: http://localhost:8000"
echo "Для остановки нажмите Ctrl+C"
echo "=========================================="

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
