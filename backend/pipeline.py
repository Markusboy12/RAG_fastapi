"""
RAG Pipeline with HyDE (Hypothetical Document Embeddings)
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
    HyDE (Hypothetical Document Embeddings) query transformation.
    Generates hypothetical answer/code for improved search.
    """
    
    def __init__(self):
        self.llm = Groq(
            model=settings.groq_model,
            api_key=settings.groq_api_key
        )
    
    async def transform(self, query: str) -> str:
        """
        Generate hypothetical document/code from query
        
        Args:
            query: Original user query
            
        Returns:
            Hypothetical document/code
        """
        prompt = f"""You are a FastAPI expert. Generate a hypothetical code example or documentation 
that could answer the following question. Do not answer the question directly, 
just create a realistic code snippet or documentation that would contain relevant information.

Question: {query}

Hypothetical FastAPI code/documentation:"""

        response = await self.llm.acomplete(prompt)
        return response.text.strip()


class RAGPipeline:
    """
    RAG pipeline with HyDE, memory, and streaming support
    """
    
    def __init__(self):
        # Initialize LLM
        self.llm = Groq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            streaming=True
        )
        
        # Initialize embeddings
        self.embed_model = VoyageAIEmbedding(
            model_name=settings.voyage_model,
            api_key=settings.voyage_api_key
        )
        
        # Configure LlamaIndex
        LlamaSettings.llm = self.llm
        LlamaSettings.embed_model = self.embed_model
        LlamaSettings.chunk_size = settings.chunk_size
        
        # Initialize Qdrant
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection_name
        )
        
        # HyDE transformer
        self.hyde = HyDETransform()
        
        # Index (will be set during load)
        self.index: Optional[VectorStoreIndex] = None
        
        # Redis memory
        self.redis_memory: Optional[RedisChatMemoryBuffer] = None
    
    async def initialize(self) -> None:
        """Initialize index and memory"""
        # Load existing index from Qdrant
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )
        
        # Initialize Redis memory
        self.redis_memory = RedisChatMemoryBuffer(
            redis_url=settings.redis_url,
            key_prefix=settings.redis_chat_key_prefix,
            max_tokens=settings.memory_window * 512  # Approximate token size
        )
    
    def _create_retriever(self, query: str):
        """Create retriever with hybrid search"""
        return VectorIndexRetriever(
            index=self.index,
            similarity_top_k=settings.top_k_chunks,
            vector_store_query_mode="hybrid"  # Hybrid search: keyword + vector
        )
    
    async def _apply_hyde(self, query: str) -> str:
        """Apply HyDE transformation"""
        try:
            hypothetical_doc = await self.hyde.transform(query)
            # Combine original query with hypothetical document
            enriched_query = f"{query}\n\nContext: {hypothetical_doc}"
            return enriched_query
        except Exception as e:
            print(f"HyDE error: {e}")
            return query  # Fallback to original query
    
    async def chat_stream(
        self, 
        query: str, 
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Streaming response using RAG + HyDE + Memory
        
        Args:
            query: User query
            session_id: Session ID for memory
            
        Yields:
            Response tokens
        """
        if not self.index:
            await self.initialize()
        
        # Apply HyDE
        enriched_query = await self._apply_hyde(query)
        
        # Get history from Redis
        chat_history = []
        if self.redis_memory:
            try:
                chat_history = await self.redis_memory.aget(session_id=session_id)
            except Exception as e:
                print(f"Redis error: {e}")
        
        # Create retriever
        retriever = self._create_retriever(enriched_query)
        
        # Retrieve documents
        nodes = await retriever.aretrieve(enriched_query)
        
        # Post-processing (filter by relevance)
        if nodes:
            postprocessor = SimilarityPostprocessor(
                similarity_cutoff=0.5  # Minimum relevance threshold
            )
            filtered_nodes = postprocessor.postprocess_nodes(nodes)
        else:
            filtered_nodes = []
        
        # Build context
        context_text = "\n\n".join([node.get_content() for node in filtered_nodes])
        
        # Assemble prompt with history and context
        system_prompt = """You are an experienced FastAPI assistant. Answer accurately and concisely, 
providing code examples where appropriate. Use the provided documentation context.
If the context doesn't contain the needed information, say so honestly."""

        history_text = ""
        if chat_history:
            history_text = "\n".join([
                f"User: {msg['role']}\nAssistant: {msg['content']}" 
                for msg in chat_history[-settings.memory_window:]
            ])
        
        full_prompt = f"""{system_prompt}

Dialogue history:
{history_text}

Documentation context:
{context_text}

User question: {query}

Answer:"""
        
        # Streaming response from LLM
        response = await self.llm.astream_complete(full_prompt)
        
        async for token in response:
            yield token.delta or ""
        
        # Save to history
        if self.redis_memory:
            try:
                await self.redis_memory.aput(
                    session_id=session_id,
                    role="user",
                    content=query
                )
                # Full response will be saved after stream completes
            except Exception as e:
                print(f"Redis save error: {e}")
    
    async def chat_sync(self, query: str, session_id: str) -> str:
        """
        Synchronous response (fallback)
        
        Args:
            query: User query
            session_id: Session ID
            
        Returns:
            Full response
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
        """Save message to Redis"""
        if self.redis_memory:
            try:
                await self.redis_memory.aput(
                    session_id=session_id,
                    role=role,
                    content=content
                )
            except Exception as e:
                print(f"Redis save error: {e}")


# Singleton instance
_pipeline: Optional[RAGPipeline] = None


async def get_pipeline() -> RAGPipeline:
    """Get singleton pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
        await _pipeline.initialize()
    return _pipeline
