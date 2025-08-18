"""
Milvus vector database integration for storing and searching embeddings
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
import json
from pymilvus import (
    connections, 
    Collection, 
    CollectionSchema, 
    FieldSchema, 
    DataType,
    utility
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Custom exception for vector store operations"""
    pass


class MilvusVectorStore:
    """Milvus vector database client for embedding storage and retrieval"""
    
    def __init__(self):
        settings = get_settings()
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.connection_name = "default"
        self.dimension = 4096  # Qwen3-Embedding-8B dimension
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Milvus"""
        try:
            connections.connect(
                alias=self.connection_name,
                host=self.host,
                port=self.port
            )
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise VectorStoreError(f"Milvus connection failed: {e}")
    
    def _ensure_connected(self) -> None:
        """Ensure we're connected to Milvus"""
        if not self._connected:
            raise VectorStoreError("Not connected to Milvus. Call connect() first.")
    
    def create_collection_schema(self, collection_name: str) -> None:
        """Create a collection schema for document chunks"""
        self._ensure_connected()
        
        try:
            # Check if collection already exists
            if utility.has_collection(collection_name):
                logger.info(f"Collection '{collection_name}' already exists")
                return
            
            # Define fields
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="chunk_id", dtype=DataType.INT64, description="Database chunk ID"),
                FieldSchema(name="document_id", dtype=DataType.INT64, description="Database document ID"),
                FieldSchema(name="collection_id", dtype=DataType.INT64, description="Database collection ID"),
                FieldSchema(name="chunk_index", dtype=DataType.INT64, description="Chunk position in document"),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535, description="Chunk text content"),
                FieldSchema(name="char_count", dtype=DataType.INT64, description="Character count"),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=8192, description="JSON metadata"),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension, description="Text embedding")
            ]
            
            # Create schema
            schema = CollectionSchema(
                fields=fields,
                description=f"Vector store for collection: {collection_name}"
            )
            
            # Create collection
            collection = Collection(name=collection_name, schema=schema)
            
            # Create index for vector search
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            
            logger.info(f"Created Milvus collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise VectorStoreError(f"Collection creation failed: {e}")
    
    def get_collection_name(self, kb_collection_id: int) -> str:
        """Generate Milvus collection name from KB collection ID"""
        return f"kb_collection_{kb_collection_id}"
    
    async def store_embeddings(
        self, 
        kb_collection_id: int,
        chunks_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store chunk embeddings in Milvus
        
        Args:
            kb_collection_id: Knowledge base collection ID
            chunks_data: List of dicts with keys: chunk_id, document_id, chunk_index, 
                        text, char_count, embedding, metadata
        
        Returns:
            List of Milvus IDs for the stored embeddings
        """
        self._ensure_connected()
        
        if not chunks_data:
            return []
        
        collection_name = self.get_collection_name(kb_collection_id)
        
        try:
            # Ensure collection exists
            self.create_collection_schema(collection_name)
            
            collection = Collection(collection_name)
            
            # Prepare data for insertion
            chunk_ids = []
            document_ids = []
            collection_ids = []
            chunk_indices = []
            texts = []
            char_counts = []
            metadatas = []
            embeddings = []
            
            for chunk_data in chunks_data:
                chunk_ids.append(chunk_data["chunk_id"])
                document_ids.append(chunk_data["document_id"])
                collection_ids.append(kb_collection_id)
                chunk_indices.append(chunk_data["chunk_index"])
                texts.append(chunk_data["text"])
                char_counts.append(chunk_data["char_count"])
                metadatas.append(json.dumps(chunk_data.get("metadata", {})))
                embeddings.append(chunk_data["embedding"])
            
            # Insert data
            entities = [
                chunk_ids,
                document_ids,
                collection_ids,
                chunk_indices,
                texts,
                char_counts,
                metadatas,
                embeddings
            ]
            
            insert_result = collection.insert(entities)
            
            # Flush to ensure data is written
            collection.flush()
            
            # Load collection for search
            collection.load()
            
            milvus_ids = [str(id_) for id_ in insert_result.primary_keys]
            
            logger.info(f"Stored {len(milvus_ids)} embeddings in collection {collection_name}")
            return milvus_ids
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {e}")
            raise VectorStoreError(f"Embedding storage failed: {e}")
    
    async def search_similar(
        self, 
        kb_collection_id: int,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings
        
        Returns:
            List of dicts with keys: milvus_id, chunk_id, document_id, text, score, metadata
        """
        self._ensure_connected()
        
        collection_name = self.get_collection_name(kb_collection_id)
        
        try:
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection {collection_name} does not exist")
                return []
            
            collection = Collection(collection_name)
            
            # Ensure collection is loaded
            collection.load()
            
            # Search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Perform search
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                output_fields=["chunk_id", "document_id", "chunk_index", "text", "char_count", "metadata"]
            )
            
            # Process results
            similar_chunks = []
            for hits in results:
                for hit in hits:
                    if hit.score >= score_threshold:
                        metadata = {}
                        try:
                            metadata = json.loads(hit.entity.get("metadata", "{}"))
                        except:
                            pass
                        
                        similar_chunks.append({
                            "milvus_id": str(hit.id),
                            "chunk_id": hit.entity.get("chunk_id"),
                            "document_id": hit.entity.get("document_id"),
                            "chunk_index": hit.entity.get("chunk_index"),
                            "text": hit.entity.get("text"),
                            "char_count": hit.entity.get("char_count"),
                            "score": float(hit.score),
                            "metadata": metadata
                        })
            
            logger.info(f"Found {len(similar_chunks)} similar chunks (threshold: {score_threshold})")
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            raise VectorStoreError(f"Embedding search failed: {e}")
    
    async def delete_document_embeddings(self, kb_collection_id: int, document_id: int) -> int:
        """Delete all embeddings for a document"""
        self._ensure_connected()
        
        collection_name = self.get_collection_name(kb_collection_id)
        
        try:
            if not utility.has_collection(collection_name):
                logger.warning(f"Collection {collection_name} does not exist")
                return 0
            
            collection = Collection(collection_name)
            
            # Delete by document_id
            expr = f"document_id == {document_id}"
            delete_result = collection.delete(expr)
            
            # Flush to ensure deletion
            collection.flush()
            
            deleted_count = delete_result.delete_count
            logger.info(f"Deleted {deleted_count} embeddings for document {document_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete document embeddings: {e}")
            raise VectorStoreError(f"Embedding deletion failed: {e}")
    
    async def delete_collection_embeddings(self, kb_collection_id: int) -> bool:
        """Delete entire collection and all its embeddings"""
        self._ensure_connected()
        
        collection_name = self.get_collection_name(kb_collection_id)
        
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Deleted Milvus collection: {collection_name}")
                return True
            else:
                logger.warning(f"Collection {collection_name} does not exist")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise VectorStoreError(f"Collection deletion failed: {e}")


# Global vector store instance
vector_store = MilvusVectorStore()