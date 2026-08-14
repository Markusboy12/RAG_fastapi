"""
Configuration for FastAPI RAG Agent Application
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM Settings
    groq_api_key: str
    groq_model: str = "qwen/qwen-3-27b"
    
    # Voyage AI Embeddings
    voyage_api_key: str
    voyage_model: str = "voyage-code-3"
    
    # Qdrant Vector Store
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str = "fastapi_docs"
    
    # Redis Memory
    redis_url: str = "redis://localhost:6379"
    redis_chat_key_prefix: str = "chat_memory_"
    
    # Firecrawl API
    firecrawl_api_key: str | None = None
    
    # Application Settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    
    # RAG Parameters
    top_k_chunks: int = 5
    memory_window: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 50


settings = Settings()
