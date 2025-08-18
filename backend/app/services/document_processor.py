"""
Document processing pipeline that coordinates text extraction, chunking, and embedding generation
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.text_processing import document_analyzer, TextChunk
from app.services.ollama_client import ollama_client
from app.services.vector_store import vector_store
from app.models.knowledge_base import DocumentStatus

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Custom exception for document processing errors"""
    pass


class DocumentProcessingPipeline:
    """Complete document processing pipeline"""
    
    def __init__(self):
        self.default_embedding_model = "nomic-embed-text"
    
    async def process_document(
        self,
        document_id: int,
        collection_id: int,
        file_path: str,
        mime_type: str,
        embedding_model: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline
        
        Returns:
            Dict with processing results and statistics
        """
        embedding_model = embedding_model or self.default_embedding_model
        
        processing_start = datetime.now()
        
        try:
            logger.info(f"Starting document processing for document {document_id}")
            
            # Step 1: Extract and chunk text
            logger.info("Step 1: Extracting and chunking text")
            full_text, chunks = await document_analyzer.analyze_document(file_path, mime_type)
            
            if not chunks:
                raise ProcessingError("No chunks created from document")
            
            logger.info(f"Created {len(chunks)} chunks from document")
            
            # Step 2: Generate embeddings
            logger.info("Step 2: Generating embeddings")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = await ollama_client.generate_embeddings_batch(chunk_texts, embedding_model)
            
            # Filter out failed embeddings
            valid_chunks_and_embeddings = [
                (chunk, embedding) for chunk, embedding in zip(chunks, embeddings) 
                if embedding  # Only keep non-empty embeddings
            ]
            
            if not valid_chunks_and_embeddings:
                raise ProcessingError("Failed to generate any valid embeddings")
            
            logger.info(f"Generated {len(valid_chunks_and_embeddings)} valid embeddings")
            
            # Step 3: Store in vector database
            logger.info("Step 3: Storing embeddings in vector database")
            
            # Prepare data for vector store
            chunks_data = []
            for i, (chunk, embedding) in enumerate(valid_chunks_and_embeddings):
                chunk_data = {
                    "chunk_id": chunk.id if hasattr(chunk, 'id') and chunk.id else (document_id * 1000 + chunk.chunk_index),  # Use actual chunk ID or generate one
                    "document_id": document_id,
                    "collection_id": collection_id,  # Fix: use collection_id parameter, not document.collection_id
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "char_count": chunk.char_count,
                    "embedding": embedding,
                    "metadata": json.dumps({
                        "start_pos": chunk.start_pos,
                        "end_pos": chunk.end_pos,
                        "hash": chunk.hash,
                        "processing_time": processing_start.isoformat()
                    })
                }
                chunks_data.append(chunk_data)
            
            # Connect to vector store if not already connected
            try:
                await vector_store.connect()
            except Exception as e:
                logger.warning(f"Vector store connection failed: {e}")
                # Continue without vector storage for now
            
            # Store embeddings
            milvus_ids = []
            try:
                milvus_ids = await vector_store.store_embeddings(collection_id, chunks_data)
                logger.info(f"Stored {len(milvus_ids)} embeddings in Milvus")
            except Exception as e:
                logger.warning(f"Vector storage failed: {e}")
                # Continue without vector storage
            
            # Step 3.5: Store chunks in SQL database
            logger.info("Step 3.5: Storing chunks in SQL database")
            sql_chunks_stored = 0
            if db:
                try:
                    from app.models.knowledge_base import KBChunk
                    
                    # Store chunks in SQL database
                    for i, (chunk, embedding) in enumerate(valid_chunks_and_embeddings):
                        milvus_id = milvus_ids[i] if i < len(milvus_ids) else None
                        
                        sql_chunk = KBChunk(
                            document_id=document_id,
                            chunk_index=chunk.chunk_index,
                            text=chunk.text,
                            # char_count is auto-generated by MySQL based on text length
                            milvus_id=str(milvus_id) if milvus_id else None
                        )
                        db.add(sql_chunk)
                    
                    await db.flush()  # Save all chunks
                    sql_chunks_stored = len(valid_chunks_and_embeddings)
                    logger.info(f"Stored {sql_chunks_stored} chunks in SQL database")
                    
                except Exception as e:
                    logger.warning(f"SQL chunk storage failed: {e}")
                    # Continue without SQL storage
            else:
                logger.warning("No database session provided, skipping SQL chunk storage")
            
            # Step 4: Generate document summary and keywords
            logger.info("Step 4: Generating document summary and keywords")
            
            # Use first few chunks for summary (limit text length)
            summary_text = " ".join([chunk.text for chunk in chunks[:3]])[:2000]
            
            try:
                summary = await ollama_client.summarize_text(summary_text)
                keywords = await ollama_client.extract_keywords(summary_text)
            except Exception as e:
                logger.warning(f"Summary/keywords generation failed: {e}")
                summary = "Summary not available"
                keywords = []
            
            processing_end = datetime.now()
            processing_time = (processing_end - processing_start).total_seconds()
            
            # Return processing results
            results = {
                "status": "success",
                "document_id": document_id,
                "collection_id": collection_id,
                "processing_time_seconds": processing_time,
                "text_extraction": {
                    "full_text_length": len(full_text),
                    "total_chunks": len(chunks),
                    "valid_chunks": len(valid_chunks_and_embeddings),
                },
                "embeddings": {
                    "model": embedding_model,
                    "generated_count": len(valid_chunks_and_embeddings),
                    "stored_count": len(milvus_ids),
                    "milvus_ids": milvus_ids
                },
                "chunks_stored": sql_chunks_stored,
                "analysis": {
                    "summary": summary,
                    "keywords": keywords
                },
                "chunks": [
                    {
                        "index": chunk.chunk_index,
                        "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text,
                        "char_count": chunk.char_count,
                        "has_embedding": bool(embedding),
                        "milvus_id": milvus_ids[i] if i < len(milvus_ids) else None
                    }
                    for i, (chunk, embedding) in enumerate(valid_chunks_and_embeddings)
                ]
            }
            
            logger.info(f"Document processing completed successfully in {processing_time:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            processing_time = (datetime.now() - processing_start).total_seconds()
            
            return {
                "status": "failed",
                "document_id": document_id,
                "collection_id": collection_id,
                "processing_time_seconds": processing_time,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def reprocess_document(
        self,
        document_id: int,
        collection_id: int,
        file_path: str,
        mime_type: str,
        embedding_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reprocess a document (clean up old embeddings first)"""
        
        try:
            # Clean up existing embeddings
            logger.info(f"Cleaning up existing embeddings for document {document_id}")
            try:
                await vector_store.connect()
                await vector_store.delete_document_embeddings(collection_id, document_id)
            except Exception as e:
                logger.warning(f"Failed to clean up existing embeddings: {e}")
            
            # Process document
            return await self.process_document(
                document_id, collection_id, file_path, mime_type, embedding_model
            )
            
        except Exception as e:
            logger.error(f"Document reprocessing failed: {e}")
            raise ProcessingError(f"Reprocessing failed: {e}")
    
    async def search_similar_content(
        self,
        collection_id: int,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        embedding_model: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Search for similar content in a collection"""
        
        # Get user's embedding model if database session is provided
        if not embedding_model and db:
            try:
                embedding_model = await ollama_client.get_user_embedding_model(db)
            except Exception as e:
                logger.warning(f"Failed to get user embedding model, using default: {e}")
                embedding_model = self.default_embedding_model
        else:
            embedding_model = embedding_model or self.default_embedding_model
        
        try:
            logger.info(f"Searching for similar content in collection {collection_id}")
            
            # Generate query embedding with timeout
            import asyncio
            query_embedding = await asyncio.wait_for(
                ollama_client.generate_embedding(query_text, embedding_model),
                timeout=30.0
            )
            
            # Connect to vector store with timeout
            await asyncio.wait_for(vector_store.connect(), timeout=5.0)
            
            # Search for similar chunks with timeout
            results = await asyncio.wait_for(
                vector_store.search_similar(collection_id, query_embedding, limit, score_threshold),
                timeout=10.0
            )
            
            logger.info(f"Found {len(results)} similar chunks")
            return {
                "matches": results,
                "total_matches": len(results),
                "query": query_text,
                "collection_id": collection_id
            }
            
        except asyncio.TimeoutError as e:
            logger.error(f"Content search timed out: {e}")
            raise ProcessingError(f"Search failed: Milvus connection timed out")
        except Exception as e:
            logger.error(f"Content search failed: {e}")
            raise ProcessingError(f"Search failed: {e}")
    
    async def get_processing_status(self, document_id: int) -> Dict[str, Any]:
        """Get processing status for a document (placeholder for future async processing)"""
        
        # This would be enhanced to track actual async processing status
        # For now, return a simple status
        return {
            "document_id": document_id,
            "status": "completed",  # or "processing", "pending", "failed"
            "progress": 1.0,
            "message": "Processing completed"
        }


# Global processing pipeline instance
processing_pipeline = DocumentProcessingPipeline()