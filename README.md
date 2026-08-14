# FastAPI RAG Agent with HyDE

Intelligent RAG agent for working with FastAPI documentation, using **Simple RAG + HyDE** (Hypothetical Document Embeddings) architecture to improve search accuracy for code and examples.

## 🚀 Features

- **HyDE (Hypothetical Document Embeddings)**: Generates hypothetical code before search to improve relevance
- **Hybrid Search**: Combines vector and keyword search in Qdrant
- **Streaming Responses**: Real-time token streaming via Server-Sent Events (SSE)
- **Memory**: Dialogue history in Redis for contextual responses
- **Code Highlighting**: Python/FastAPI syntax highlighting on the frontend
- **Fallback LLM**: Automatic switch to Ollama when Groq errors occur
- **Free Tier Ready**: All services work on free tiers

## 🏗️ Architecture

```
User Query → HyDE (Groq) → Voyage AI Embeddings → Qdrant Hybrid Search 
           → Grade → Redis Memory → Groq Streaming → SSE → Browser
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM (Primary)** | Groq API (Qwen-2.5-Coder-32B) | Generate HyDE queries and responses |
| **LLM (Fallback)** | Ollama Cloud | Backup LLM for Groq errors |
| **Embeddings** | Voyage AI (voyage-code-3) | Vectorize code and documentation |
| **Vector DB** | Qdrant Cloud | Hybrid search (vector + keyword) |
| **Memory** | Redis Cloud | Message history + embedding cache |
| **Parser** | Firecrawl API | Extract docs.fastapi.dev → Markdown |
| **Backend** | FastAPI 0.115+ | REST API + SSE streaming |
| **Frontend** | Vanilla HTML/JS | Chat UI + highlight.js |
| **RAG Orchestrator** | LlamaIndex 0.12+ | Chunking, HyDE, retrieval, memory |

## 📋 Requirements

- Python 3.11+
- uv or poetry (uv recommended)
- Docker (optional, for local Redis/Qdrant)

## 🔑 Required API Keys

Get free keys for the following services:

| Service | URL | Free Tier Limits |
|---------|-----|------------------|
| **Groq** | https://console.groq.com | ~30 req/min |
| **Voyage AI** | https://dashboard.voyageai.com | 200M tokens/month |
| **Qdrant** | https://cloud.qdrant.io | 1 GB storage |
| **Redis** | https://redis.com/try-free | 30 MB |
| **Firecrawl** | https://www.firecrawl.dev | 500 pages/month |

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd fastapi-rag-agent
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LLM
GROQ_API_KEY=gsk_...
OLLAMA_BASE_URL=http://localhost:11434  # optional

# Embeddings
VOYAGE_API_KEY=...

# Vector DB
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=fastapi_docs

# Memory & Cache
REDIS_URL=rediss://default:password@host:6379

# Parser
FIRECRAWL_API_KEY=fc_...  # optional, can use direct parsing

# App Settings
LOG_LEVEL=INFO
MAX_MEMORY_MESSAGES=5
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
```

### 3. Install dependencies

It is recommended to use **uv** for fast installation:

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

Or via pip:

```bash
pip install -r requirements.txt
```

## 🚀 Running

### Step 1: Index documentation

Load FastAPI documentation into the vector database:

```bash
uv run python -m backend.indexer
```

Process:
1. Firecrawl extracts pages from `docs.fastapi.dev`
2. LlamaIndex splits into chunks (512 tokens, overlap 50)
3. Voyage AI generates embeddings
4. Chunks are saved to Qdrant with metadata

⏱️ Execution time: ~5-10 minutes

### Step 2: Start the server

```bash
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the script:

```bash
./scripts/run.sh
```

### Step 3: Open the interface

Open in browser: **http://localhost:8000**

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Static frontend (Chat UI) |
| `POST` | `/chat` | SSE streaming response |
| `POST` | `/chat/sync` | JSON response (fallback) |
| `GET` | `/health` | Health check |
| `POST` | `/index/rebuild` | Rebuild document index |

### Example curl request

```bash
# Streaming request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "how to implement JWT authentication in FastAPI?"}'
```

## 💬 Example queries

Try asking the agent these questions:

- *"How to create an endpoint with OAuth2PasswordBearer?"*
- *"Show me an example dependency for JWT token validation"*
- *"How to validate request body using Pydantic?"*
- *"Explain the difference between Depends and Security"*
- *"How to configure CORS middleware?"*

## 🧪 Testing

Run tests (if added):

```bash
uv run pytest tests/ -v
```

## 🐳 Docker (optional)

For local Redis and Qdrant:

```bash
docker-compose up -d
```

Update `.env` to use local services:

```env
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

## 📁 Project structure

```
fastapi-rag-agent/
├── backend/
│   ├── __init__.py
│   ├── config.py          # Settings and env variables
│   ├── indexer.py         # Document loading and indexing
│   ├── pipeline.py        # RAG pipeline (HyDE, retrieval, memory)
│   └── main.py            # FastAPI server + endpoints
├── frontend/
│   ├── index.html         # Chat UI
│   ├── styles.css         # Styles
│   └── app.js             # SSE client + highlight.js
├── scripts/
│   └── run.sh             # Launch script
├── tests/                 # Tests (optional)
├── pyproject.toml         # Dependencies
├── .env.example           # Environment variable template
├── .gitignore
└── README.md              # This file
```

## 🔧 Parameter configuration

In `.env` you can configure:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CHUNK_SIZE` | 512 | Chunk size in tokens |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks |
| `TOP_K_RESULTS` | 5 | Number of search results |
| `MAX_MEMORY_MESSAGES` | 5 | History messages in Redis |
| `HYDE_MODEL` | qwen-2.5-coder-32b | Model for HyDE |
| `RESPONSE_MODEL` | qwen-2.5-coder-32b | Model for response generation |

## 🛠️ Troubleshooting

### Qdrant connection error
- Check `QDRANT_URL` and `QDRANT_API_KEY`
- Make sure the collection is created (`indexer.py` creates automatically)

### Groq API error
- Check rate limiting limits (~30 req/min on free tier)
- Enable fallback to Ollama for frequent errors

### Slow indexing
- Reduce `CHUNK_SIZE` or parallelize loading
- Firecrawl free tier: 500 pages/month

### Empty responses
- Check that indexing completed successfully
- Increase `TOP_K_RESULTS` to 10

## 📊 Monitoring

Logging is configured via Python's standard `logging` module.

Log level: `LOG_LEVEL=INFO` (can be changed to `DEBUG`)

Key metrics to track:
- Response time (time to first token)
- Number of chunks in context
- Relevance score of search results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License

## 🔗 Useful links

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [LlamaIndex Docs](https://docs.llamaindex.ai)
- [HyDE Paper](https://arxiv.org/abs/2212.10496)
- [Qdrant Documentation](https://qdrant.tech/documentation)
- [Groq Cloud](https://console.groq.com)
- [Voyage AI Embeddings](https://docs.voyageai.com/docs/embeddings)

---

**Made with ❤️ for the FastAPI community**