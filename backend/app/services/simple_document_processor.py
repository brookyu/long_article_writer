"""
Simple Document Processor
Inspired by Open WebUI's robust approach to document processing.
Uses Apache Tika for reliable text extraction.
"""

import asyncio
import aiohttp
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge_base import KBDocument, KBChunk, DocumentStatus
from app.services.text_processing import DocumentProcessor as TextProcessor
from app.services.ollama_client import OllamaClient
from app.services.vector_store import MilvusVectorStore

logger = logging.getLogger(__name__)

class SimpleDocumentProcessor:
    """
    Simplified document processor inspired by Open WebUI's approach.
    Key principles:
    1. Use Apache Tika for reliable text extraction
    2. Simple, synchronous processing (no complex job queues)
    3. Immediate feedback to users
    4. Robust error handling
    """
    
    def __init__(self):
        self.tika_url = "http://localhost:9998"
        self.text_processor = TextProcessor()
        self.ollama_client = OllamaClient()
        self.vector_store = MilvusVectorStore()
    
    async def process_document(
        self,
        file_path: Path,
        collection_id: int,
        db: AsyncSession,
        original_filename: str = None,
        mime_type: str = None
    ) -> Dict[str, Any]:
        """
        Process a single document using Open WebUI's proven approach.
        Returns immediate results without complex job tracking.
        """
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Step 1: Calculate file hash for deduplication
            file_hash = await self._calculate_file_hash(file_path)
            
            # Step 2: Check for duplicates and replace if exists
            existing_doc_result = await db.execute(
                select(KBDocument).where(
                    KBDocument.collection_id == collection_id,
                    KBDocument.sha256 == file_hash
                )
            )
            existing_doc = existing_doc_result.scalar_one_or_none()
            
            if existing_doc:
                logger.info(f"🔄 Found existing document {existing_doc.id} - replacing it with new version")

                # Delete existing chunks from SQL and vector store
                existing_chunks_result = await db.execute(
                    select(KBChunk).where(KBChunk.document_id == existing_doc.id)
                )
                existing_chunks = existing_chunks_result.scalars().all()
                
                # Remove from vector store if connected
                if self.vector_store._connected and existing_chunks:
                    try:
                        deleted_count = await self.vector_store.delete_document_embeddings(collection_id, existing_doc.id)
                        logger.info(f"🗑️ Removed {deleted_count} embeddings from vector store")
                    except Exception as e:
                        logger.warning(f"Failed to remove embeddings from vector store: {e}")
                
                # Delete chunks from SQL
                for chunk in existing_chunks:
                    await db.delete(chunk)
                
                # Delete the document
                await db.delete(existing_doc)
                await db.flush()
                logger.info(f"🗑️ Removed existing document and {len(existing_chunks)} chunks")
            
            # Step 3: Extract text using Apache Tika (Open WebUI's approach)
            text_content = await self._extract_text_with_tika(file_path)
            
            if not text_content.strip():
                return {
                    "success": False,
                    "error": "No text content extracted",
                    "filename": original_filename or file_path.name
                }
            
            # Step 4: Create document record
            document = KBDocument(
                collection_id=collection_id,
                filename=file_path.name,
                original_filename=original_filename or file_path.name,
                size_bytes=file_path.stat().st_size,
                sha256=file_hash,
                file_path=str(file_path),
                mime_type=mime_type or self._get_mime_type(file_path),
                status=DocumentStatus.PROCESSING
            )
            
            db.add(document)
            await db.flush()  # Get document ID
            
            # Step 5: Chunk the text
            chunks = self.text_processor.create_chunks(text_content)
            
            # Step 6: Generate embeddings and store chunks
            logger.info(f"📊 Processing {len(chunks)} chunks for {original_filename or file_path.name}")
            embedding_model = await self.ollama_client.get_user_embedding_model(db)
            logger.info(f"🎯 Using embedding model: {embedding_model}")
            stored_chunks = 0
            
            # Ensure vector store is connected with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if not self.vector_store._connected:
                        await self.vector_store.connect()
                    break
                except Exception as e:
                    logger.warning(f"Milvus connection attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2)  # Wait before retry
            
            for i, chunk in enumerate(chunks):
                try:
                    # Generate embedding with retries
                    embedding = None
                    max_embedding_retries = 3
                    for attempt in range(max_embedding_retries):
                        try:
                            logger.info(f"Generating embedding for chunk {i}/{len(chunks)} (attempt {attempt + 1}/{max_embedding_retries})")
                            embedding = await self.ollama_client.generate_embedding(
                                chunk.text,
                                embedding_model
                            )
                            logger.info(f"✅ Successfully generated embedding for chunk {i}")
                            break
                        except Exception as e:
                            logger.error(f"❌ Embedding attempt {attempt + 1}/{max_embedding_retries} failed for chunk {i}: {e}")
                            if attempt == max_embedding_retries - 1:
                                raise Exception(f"Failed to generate embedding after {max_embedding_retries} attempts: {e}")
                            await asyncio.sleep(2)  # Wait before retry
                    
                    if not embedding:
                        raise Exception("No embedding generated")
                    
                    # Store chunk in SQL database
                    db_chunk = KBChunk(
                        document_id=document.id,
                        chunk_index=i,
                        text=chunk.text
                        # Note: char_count is computed automatically
                    )
                    
                    db.add(db_chunk)
                    await db.flush()  # Get chunk ID
                    
                    # Store embedding in vector database (Milvus) with fallback
                    vector_stored = False
                    if self.vector_store._connected:
                        try:
                            await self.vector_store.add_embeddings(
                                embeddings=[embedding],
                                metadatas=[{
                                    "document_id": document.id,
                                    "chunk_id": db_chunk.id,
                                    "chunk_index": i,
                                    "filename": document.filename
                                }],
                                ids=[f"doc_{document.id}_chunk_{i}"]
                            )
                            vector_stored = True
                            logger.debug(f"Stored embedding for chunk {i} in vector database")
                        except Exception as e:
                            logger.warning(f"Failed to store embedding for chunk {i} in vector database: {e}")
                            # Continue processing without vector storage
                    
                    if not vector_stored:
                        logger.info(f"Chunk {i} stored in SQL database only (vector storage skipped)")
                    
                    stored_chunks += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process chunk {i}: {e}")
                    continue
            
            # Step 7: Update document status
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = stored_chunks
            
            await db.commit()
            
            return {
                "success": True,
                "document_id": document.id,
                "chunks_created": stored_chunks,
                "filename": original_filename or file_path.name,
                "text_length": len(text_content)
            }
            
        except Exception as e:
            logger.error(f"Document processing failed for {file_path.name}: {e}")
            logger.error(f"Full error details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Update document status to failed if created
            if 'document' in locals():
                try:
                    document.status = DocumentStatus.FAILED
                    document.error_message = str(e)
                    await db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update document status: {commit_error}")
                    await db.rollback()
            
            return {
                "success": False,
                "error": str(e),
                "filename": original_filename or file_path.name
            }
    
    async def _extract_text_with_tika(self, file_path: Path) -> str:
        """
        Extract text using Apache Tika (Open WebUI's proven approach).
        Much more reliable than individual library parsing.
        """
        try:
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as file:
                    async with session.put(
                        f"{self.tika_url}/tika",
                        data=file,
                        headers={'Accept': 'text/plain'},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            text = await response.text()
                            return text
                        else:
                            raise Exception(f"Tika extraction failed: {response.status}")
        
        except Exception as e:
            logger.error(f"Tika extraction failed for {file_path}: {e}")
            # Fallback to our existing text processing
            return await self.text_processor.extract_text_from_file(str(file_path))
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash for deduplication."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file extension."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    async def process_multiple_documents(
        self,
        file_paths: List[Path],
        collection_id: int,
        db: AsyncSession,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents with simple progress tracking.
        No complex job queues - just straightforward processing.
        """
        results = {
            "total": len(file_paths),
            "successful": [],
            "failed": [],
            "skipped": []
        }
        
        for i, file_path in enumerate(file_paths):
            try:
                result = await self.process_document(
                    file_path, collection_id, db
                )
                
                if result["success"]:
                    if result.get("skipped"):
                        results["skipped"].append(result)
                    else:
                        results["successful"].append(result)
                else:
                    results["failed"].append(result)
                
                # Simple progress callback
                if progress_callback:
                    await progress_callback({
                        "processed": i + 1,
                        "total": len(file_paths),
                        "successful": len(results["successful"]),
                        "failed": len(results["failed"]),
                        "skipped": len(results["skipped"]),
                        "percentage": ((i + 1) / len(file_paths)) * 100
                    })
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results["failed"].append({
                    "success": False,
                    "error": str(e),
                    "filename": file_path.name
                })
        
        return results