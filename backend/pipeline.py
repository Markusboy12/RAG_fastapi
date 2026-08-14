"""
RAG Pipeline с HyDE (Hypothetical Document Embeddings)
"""
import asyncio
from typing import Optional, AsyncGenerator
from llama_index.core import (
    VectorStoreIndex, 
    Settings as LlamaSettings,
    get_response_synthesizer
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.llms.groq import Groq
from llama_index.embeddings.voyageai import VoyageAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.memory.chat_redis import RedisChatMemoryBuffer
from qdrant_client import QdrantClient

from backend.config import settings


class HyDETransform:
    """
    HyDE (Hypothetical Document Embeddings) трансформация запроса.
    Генерирует гипотетический ответ/код для улучшения поиска.
    """
    
    def __init__(self):
        self.llm = Groq(
            model=settings.groq_model,
            api_key=settings.groq_api_key
        )
    
    async def transform(self, query: str) -> str:
        """
        Генерация гипотетического документа/кода по запросу
        
        Args:
            query: Исходный запрос пользователя
            
        Returns:
            Гипотетический документ/код
        """
        prompt = f"""Ты эксперт по FastAPI. Сгенерируй гипотетический пример кода или документации, 
который мог бы отвечать на следующий вопрос. Не отвечай на вопрос напрямую, 
просто создай реалистичный фрагмент кода или документации, который содержал бы релевантную информацию.

Вопрос: {query}

Гипотетический код/документация FastAPI:"""

        response = await self.llm.acomplete(prompt)
        return response.text.strip()


class RAGPipeline:
    """
    RAG пайплайн с поддержкой HyDE, памяти и streaming
    """
    
    def __init__(self):
        # Инициализация LLM
        self.llm = Groq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            streaming=True
        )
        
        # Инициализация эмбеддингов
        self.embed_model = VoyageAIEmbedding(
            model_name=settings.voyage_model,
            api_key=settings.voyage_api_key
        )
        
        # Настройка LlamaIndex
        LlamaSettings.llm = self.llm
        LlamaSettings.embed_model = self.embed_model
        LlamaSettings.chunk_size = settings.chunk_size
        
        # Инициализация Qdrant
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection_name
        )
        
        # HyDE трансформер
        self.hyde = HyDETransform()
        
        # Индекс (будет установлен при загрузке)
        self.index: Optional[VectorStoreIndex] = None
        
        # Redis память
        self.redis_memory: Optional[RedisChatMemoryBuffer] = None
    
    async def initialize(self) -> None:
        """Инициализация индекса и памяти"""
        # Загрузка существующего индекса из Qdrant
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )
        
        # Инициализация Redis памяти
        self.redis_memory = RedisChatMemoryBuffer(
            redis_url=settings.redis_url,
            key_prefix=settings.redis_chat_key_prefix,
            max_tokens=settings.memory_window * 512  # Примерный размер токенов
        )
    
    def _create_retriever(self, query: str):
        """Создание retriever с hybrid search"""
        return VectorIndexRetriever(
            index=self.index,
            similarity_top_k=settings.top_k_chunks,
            vector_store_query_mode="hybrid"  # Hybrid search: keyword + vector
        )
    
    async def _apply_hyde(self, query: str) -> str:
        """Применение HyDE трансформации"""
        try:
            hypothetical_doc = await self.hyde.transform(query)
            # Комбинируем исходный запрос с гипотетическим документом
            enriched_query = f"{query}\n\nКонтекст: {hypothetical_doc}"
            return enriched_query
        except Exception as e:
            print(f"HyDE ошибка: {e}")
            return query  # Fallback к исходному запросу
    
    async def chat_stream(
        self, 
        query: str, 
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Потоковый ответ с использованием RAG + HyDE + Memory
        
        Args:
            query: Запрос пользователя
            session_id: ID сессии для памяти
            
        Yields:
            Токены ответа
        """
        if not self.index:
            await self.initialize()
        
        # Применение HyDE
        enriched_query = await self._apply_hyde(query)
        
        # Получение истории из Redis
        chat_history = []
        if self.redis_memory:
            try:
                chat_history = await self.redis_memory.aget(session_id=session_id)
            except Exception as e:
                print(f"Redis ошибка: {e}")
        
        # Создание retriever
        retriever = self._create_retriever(enriched_query)
        
        # Retrieval документов
        nodes = await retriever.aretrieve(enriched_query)
        
        # Пост-процессинг (фильтрация по relevance)
        if nodes:
            postprocessor = SimilarityPostprocessor(
                similarity_cutoff=0.5  # Минимальный порог релевантности
            )
            filtered_nodes = postprocessor.postprocess_nodes(nodes)
        else:
            filtered_nodes = []
        
        # Формирование контекста
        context_text = "\n\n".join([node.get_content() for node in filtered_nodes])
        
        # Сборка промпта с историей и контекстом
        system_prompt = """Ты опытный помощник по FastAPI. Отвечай точно и по делу, 
приводя примеры кода где это уместно. Используй предоставленный контекст из документации.
Если контекст не содержит нужной информации, скажи об этом честно."""

        history_text = ""
        if chat_history:
            history_text = "\n".join([
                f"User: {msg['role']}\nAssistant: {msg['content']}" 
                for msg in chat_history[-settings.memory_window:]
            ])
        
        full_prompt = f"""{system_prompt}

История диалога:
{history_text}

Контекст из документации:
{context_text}

Вопрос пользователя: {query}

Ответ:"""
        
        # Streaming ответ от LLM
        response = await self.llm.astream_complete(full_prompt)
        
        async for token in response:
            yield token.delta or ""
        
        # Сохранение в историю
        if self.redis_memory:
            try:
                await self.redis_memory.aput(
                    session_id=session_id,
                    role="user",
                    content=query
                )
                # Полный ответ будет сохранён после завершения стрима
            except Exception as e:
                print(f"Redis save ошибка: {e}")
    
    async def chat_sync(self, query: str, session_id: str) -> str:
        """
        Синхронный ответ (fallback)
        
        Args:
            query: Запрос пользователя
            session_id: ID сессии
            
        Returns:
            Полный ответ
        """
        full_response = ""
        async for token in self.chat_stream(query, session_id):
            full_response += token
        return full_response
    
    async def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ) -> None:
        """Сохранение сообщения в Redis"""
        if self.redis_memory:
            try:
                await self.redis_memory.aput(
                    session_id=session_id,
                    role=role,
                    content=content
                )
            except Exception as e:
                print(f"Redis save ошибка: {e}")


# Singleton instance
_pipeline: Optional[RAGPipeline] = None


async def get_pipeline() -> RAGPipeline:
    """Получение singleton экземпляра пайплайна"""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
        await _pipeline.initialize()
    return _pipeline
