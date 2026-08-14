#!/usr/bin/env bash
# Script for quick installation and launch of FastAPI RAG Agent

set -e

echo "🚀 FastAPI RAG Agent - Installation and Launch"
echo "=============================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION found"

# Check/install uv
if ! command -v uv &> /dev/null; then
    echo "⏳ Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ uv found"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "❗ Fill in the .env file with your API keys!"
    echo "   Required keys: GROQ_API_KEY, VOYAGE_API_KEY, QDRANT_URL, QDRANT_API_KEY, REDIS_URL"
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install dependencies
echo "⏳ Installing dependencies..."
uv sync

# Index documentation
echo ""
echo "📚 Indexing FastAPI documentation..."
echo "⚠️  FIRECRAWL_API_KEY required in .env for indexing"
read -p "Run indexing now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    uv run python -m backend.indexer
fi

# Start server
echo ""
echo "🎉 Starting server..."
echo "=============================================="
echo "Open browser: http://localhost:8000"
echo "To stop, press Ctrl+C"
echo "=============================================="

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
