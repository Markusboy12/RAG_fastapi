"""
Module for loading and indexing FastAPI documentation
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
    """FastAPI documentation loader"""
    
    def __init__(self):
        self.embed_model = VoyageAIEmbedding(
            model_name=settings.voyage_model,
            api_key=settings.voyage_api_key
        )
        
        # Configure LlamaIndex
        LlamaSettings.embed_model = self.embed_model
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        # Create vector store
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection_name
        )
        
    async def create_collection(self) -> None:
        """Create collection in Qdrant if it doesn't exist"""
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
            print(f"Collection {settings.qdrant_collection_name} created")
        else:
            print(f"Collection {settings.qdrant_collection_name} already exists")
    
    async def load_from_firecrawl(self, urls: list[str]) -> list[Document]:
        """
        Load documentation via Firecrawl API
        
        Args:
            urls: List of URLs to parse
            
        Returns:
            List of documents
        """
        if not settings.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY not configured")
        
        from firecrawl import FirecrawlApp
        
        app = FirecrawlApp(api_key=settings.firecrawl_api_key)
        documents = []
        
        for url in urls:
            try:
                # Scrape page
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
                    print(f"Loaded: {url}")
                    
            except Exception as e:
                print(f"Error loading {url}: {e}")
        
        return documents
    
    async def load_docs_fastapi(self) -> list[Document]:
        """
        Load documentation from docs.fastapi.dev
        
        Returns:
            List of documents
        """
        # Main sections of FastAPI documentation
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
            print("Firecrawl API key not configured. Use manual loading.")
            return []
    
    async def index_documents(
        self, 
        documents: list[Document],
        use_code_splitter: bool = True
    ) -> VectorStoreIndex:
        """
        Index documents
        
        Args:
            documents: List of documents to index
            use_code_splitter: Use CodeSplitter for code
            
        Returns:
            Vector index
        """
        if use_code_splitter:
            # CodeSplitter is optimal for Python/FastAPI code
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
        
        # Create index with Qdrant
        index = VectorStoreIndex(
            nodes=nodes,
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )
        
        print(f"Indexed {len(nodes)} chunks")
        return index
    
    async def setup_and_index(self) -> VectorStoreIndex:
        """
        Full setup: create collection + load + index
        
        Returns:
            Vector index
        """
        await self.create_collection()
        documents = await self.load_docs_fastapi()
        
        if not documents:
            raise ValueError("Failed to load documents")
        
        index = await self.index_documents(documents)
        return index


async def main():
    """Entry point for documentation indexing"""
    loader = DocumentationLoader()
    index = await loader.setup_and_index()
    print("Indexing completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
