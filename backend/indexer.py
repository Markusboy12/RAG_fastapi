"""
Модуль для загрузки и индексации документации FastAPI
"""
import asyncio
from typing import Optional
from llama_index.core import Document, VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.node_parser import CodeSplitter
from llama_index.embeddings.voyageai import VoyageAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from backend.config import settings


class DocumentationLoader:
    """Загрузчик документации FastAPI"""
    
    def __init__(self):
        self.embed_model = VoyageAIEmbedding(
            model_name=settings.voyage_model,
            api_key=settings.voyage_api_key
        )
        
        # Настройка LlamaIndex
        LlamaSettings.embed_model = self.embed_model
        
        # Инициализация Qdrant клиента
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        # Создание векторного хранилища
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection_name
        )
        
    async def create_collection(self) -> None:
        """Создание коллекции в Qdrant если не существует"""
        collections = self.qdrant_client.get_collections().collections
        collection_exists = any(
            c.name == settings.qdrant_collection_name 
            for c in collections
        )
        
        if not collection_exists:
            self.qdrant_client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config=VectorParams(
                    size=1536,  # voyage-code-3 dimension
                    distance=Distance.COSINE
                ),
                hnsw_config={
                    "m": 16,
                    "ef_construct": 100
                }
            )
            print(f"Коллекция {settings.qdrant_collection_name} создана")
        else:
            print(f"Коллекция {settings.qdrant_collection_name} уже существует")
    
    async def load_from_firecrawl(self, urls: list[str]) -> list[Document]:
        """
        Загрузка документации через Firecrawl API
        
        Args:
            urls: Список URL для парсинга
            
        Returns:
            Список документов
        """
        if not settings.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY не настроен")
        
        from firecrawl import FirecrawlApp
        
        app = FirecrawlApp(api_key=settings.firecrawl_api_key)
        documents = []
        
        for url in urls:
            try:
                # Scraping страницы
                result = app.scrape_url(url=url, params={'formats': ['markdown']})
                
                if result and 'markdown' in result:
                    doc = Document(
                        text=result['markdown'],
                        metadata={
                            'source': url,
                            'type': 'documentation'
                        }
                    )
                    documents.append(doc)
                    print(f"Загружено: {url}")
                    
            except Exception as e:
                print(f"Ошибка загрузки {url}: {e}")
        
        return documents
    
    async def load_docs_fastapi(self) -> list[Document]:
        """
        Загрузка документации с docs.fastapi.dev
        
        Returns:
            Список документов
        """
        # Основные разделы документации FastAPI
        urls = [
            "https://fastapi.tiangolo.com/tutorial/",
            "https://fastapi.tiangolo.com/tutorial/security/",
            "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
            "https://fastapi.tiangolo.com/advanced/",
            "https://fastapi.tiangolo.com/reference/",
        ]
        
        if settings.firecrawl_api_key:
            return await self.load_from_firecrawl(urls)
        else:
            print("Firecrawl API ключ не настроен. Используйте ручную загрузку.")
            return []
    
    async def index_documents(
        self, 
        documents: list[Document],
        use_code_splitter: bool = True
    ) -> VectorStoreIndex:
        """
        Индексация документов
        
        Args:
            documents: Список документов для индексации
            use_code_splitter: Использовать CodeSplitter для кода
            
        Returns:
            Векторный индекс
        """
        if use_code_splitter:
            # CodeSplitter оптимален для кода Python/FastAPI
            node_parser = CodeSplitter(
                language="python",
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        else:
            from llama_index.core.node_parser import SentenceSplitter
            node_parser = SentenceSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap
            )
        
        nodes = node_parser.get_nodes_from_documents(documents)
        
        # Создание индекса с Qdrant
        index = VectorStoreIndex(
            nodes=nodes,
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )
        
        print(f"Проиндексировано {len(nodes)} чанков")
        return index
    
    async def setup_and_index(self) -> VectorStoreIndex:
        """
        Полная настройка: создание коллекции + загрузка + индексация
        
        Returns:
            Векторный индекс
        """
        await self.create_collection()
        documents = await self.load_docs_fastapi()
        
        if not documents:
            raise ValueError("Не удалось загрузить документы")
        
        index = await self.index_documents(documents)
        return index


async def main():
    """Точка входа для индексации документации"""
    loader = DocumentationLoader()
    index = await loader.setup_and_index()
    print("Индексация завершена успешно!")


if __name__ == "__main__":
    asyncio.run(main())
