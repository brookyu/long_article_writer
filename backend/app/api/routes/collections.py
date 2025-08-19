"""
Collection management endpoints
"""

from typing import List
from http import HTTPStatus
import time
import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.database import get_db
from app.models.knowledge_base import KBCollection, KBDocument, Article, ArticleStatus
from app.schemas.knowledge_base import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
    APIError
)
from app.schemas.articles import ArticleResponse
from app.services.article_generator import ArticleGenerator
from app.services.ollama_client import OllamaClient
from app.services.document_processor import DocumentProcessingPipeline
from app.models.settings import Setting
from datetime import datetime
from pydantic import BaseModel

logger = structlog.get_logger(__name__)
router = APIRouter()

# Temporary in-memory storage for generated articles
# In a real implementation, this would be stored in the database
generated_articles = {}


class SearchRequest(BaseModel):
    """Request model for document search"""
    query: str


async def _start_job_processing(job_id: str):
    """Start processing an upload job in the background"""
    from app.core.database import get_db
    
    # Create a new database session for this background task
    async for db in get_db():
        try:
            from app.services.upload_manager import upload_manager
            await upload_manager.start_processing_job(job_id, db)
            break  # Exit the async for loop after processing
        except Exception as e:
            logger.error(f"Failed to start job processing for {job_id}: {e}")
            break


async def get_user_llm_model(db: AsyncSession) -> str:
    """Get the user's selected LLM model from settings"""
    try:
        # Get LLM settings from database
        result = await db.execute(
            select(Setting).where(Setting.key_alias.ilike('%llm%'))
        )
        llm_setting = result.scalar_one_or_none()
        
        if llm_setting and llm_setting.model_name:
            return llm_setting.model_name
        else:
            # Default fallback - check what models are available
            ollama_client = OllamaClient()
            if await ollama_client.check_model_availability("gpt-oss:20b"):
                return "gpt-oss:20b"  # Smaller, faster model
            else:
                return "mixtral:latest"  # Larger model fallback
                
    except Exception as e:
        logger.error(f"Failed to get user LLM model: {e}")
        return "gpt-oss:20b"  # Safe default to smaller model


async def generate_article_content(collection_id: int, article_id: int, article_data: dict):
    """Background task to generate article content using real LLM"""
    from app.core.database import get_db
    
    try:
        # Update progress
        if collection_id in generated_articles and article_id in generated_articles[collection_id]:
            generated_articles[collection_id][article_id]["progress"] = "Initializing AI article generation..."
            
        # Get user's selected LLM model from database
        from app.core.database import async_session_factory
        async with async_session_factory() as db:
            # Get user's selected LLM model
            user_model = await get_user_llm_model(db)
            logger.info(f"Using LLM model: {user_model}")
            
            # Initialize Ollama client
            ollama_client = OllamaClient()
            
            # Update progress
            generated_articles[collection_id][article_id]["progress"] = f"Generating article with {user_model}..."
            
            # Create a simple article generation prompt
            topic = article_data.get("topic", "")
            writing_style = article_data.get("writing_style", "professional")
            article_type = article_data.get("article_type", "comprehensive")
            target_length = article_data.get("target_length", "medium")
            
            # Define target word counts
            word_targets = {
                "short": "500-800",
                "medium": "1000-1500", 
                "long": "2000-3000"
            }
            target_words = word_targets.get(target_length, "1000-1500")
            
            prompt = f"""Write a {writing_style} {article_type} article about "{topic}".

Target length: {target_words} words

Requirements:
- Start with a clear title using # markdown heading
- Include an introduction section using ## heading
- Add 3-5 main sections with ## headings
- Include a conclusion section
- Write in {writing_style} style
- Make it informative and well-structured
- Use markdown formatting

Please write the complete article now:"""

            # Update progress
            generated_articles[collection_id][article_id]["progress"] = f"Writing with {user_model}..."
            
            # Generate the article using Ollama with user's selected model
            article_content = await ollama_client.generate_text(prompt, model=user_model)
            
            # Calculate word count
            word_count = len(article_content.split())
            
            # Extract title from the article content
            lines = article_content.split('\n')
            title_line = next((line for line in lines if line.startswith('# ')), None)
            title = title_line[2:].strip() if title_line else f"Article: {topic}"
            
            # Update progress
            generated_articles[collection_id][article_id]["progress"] = "Finalizing article..."
            
            # Update article with generated content
            import time
            generated_articles[collection_id][article_id].update({
                "status": "completed",
                "progress": "Article generation completed!",
                "content": article_content,
                "word_count": word_count,
                "title": title,
                "generation_time_seconds": time.time() - generated_articles[collection_id][article_id]["created_at"]
            })
            
            logger.info(f"Article {article_id} generation completed", 
                       word_count=word_count, 
                       topic=topic,
                       title=title,
                       model_used=user_model)
        
    except Exception as e:
        logger.error(f"Article generation failed: {e}", 
                    article_id=article_id, 
                    topic=article_data.get("topic"))
        
        # Mark as failed
        if collection_id in generated_articles and article_id in generated_articles[collection_id]:
            generated_articles[collection_id][article_id].update({
                "status": "failed",
                "progress": f"Generation failed: {str(e)[:100]}..."
            })


@router.post("/", response_model=CollectionResponse, status_code=HTTPStatus.CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    db: AsyncSession = Depends(get_db)
) -> CollectionResponse:
    """Create a new knowledge base collection"""
    
    # Check if collection name already exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.name == collection_data.name)
    )
    existing_collection = result.scalar_one_or_none()
    
    if existing_collection:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f"Collection with name '{collection_data.name}' already exists"
        )
    
    # Get user's configured embedding model if not specified
    embedding_model = collection_data.embedding_model
    if not embedding_model:
        ollama_client = OllamaClient()
        try:
            embedding_model = await ollama_client.get_user_embedding_model(db)
            logger.info(f"Using user's configured embedding model: {embedding_model}")
        except Exception as e:
            logger.warning(f"Failed to get user embedding model, using default: {e}")
            embedding_model = "nomic-embed-text"
    
    # Create new collection
    new_collection = KBCollection(
        name=collection_data.name,
        description=collection_data.description,
        embedding_model=embedding_model
    )
    
    db.add(new_collection)
    await db.commit()
    await db.refresh(new_collection)
    
    logger.info("Collection created", collection_id=new_collection.id, name=new_collection.name)
    
    return CollectionResponse.model_validate(new_collection)


@router.get("/", response_model=CollectionListResponse)
async def list_collections(
    db: AsyncSession = Depends(get_db)
) -> CollectionListResponse:
    """List all knowledge base collections"""
    
    # Get collections with counts
    result = await db.execute(
        select(KBCollection).order_by(KBCollection.created_at.desc())
    )
    collections = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(select(func.count(KBCollection.id)))
    total = count_result.scalar()
    
    collection_responses = []
    for col in collections:
        # Handle None values for total_documents and total_chunks
        col_dict = {
            "id": col.id,
            "name": col.name,
            "description": col.description,
            "embedding_model": col.embedding_model,
            "total_documents": col.total_documents or 0,
            "total_chunks": col.total_chunks or 0,
            "created_at": col.created_at,
            "updated_at": col.updated_at
        }
        collection_responses.append(CollectionResponse.model_validate(col_dict))
    
    return CollectionListResponse(
        collections=collection_responses,
        total=total
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
) -> CollectionResponse:
    """Get a specific collection by ID"""
    
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    return CollectionResponse.model_validate(collection)


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    collection_data: CollectionUpdate,
    db: AsyncSession = Depends(get_db)
) -> CollectionResponse:
    """Update a collection"""
    
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Check for name conflicts if name is being updated
    if collection_data.name and collection_data.name != collection.name:
        existing_result = await db.execute(
            select(KBCollection).where(KBCollection.name == collection_data.name)
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f"Collection with name '{collection_data.name}' already exists"
            )
    
    # Update fields
    update_data = collection_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)
    
    await db.commit()
    await db.refresh(collection)
    
    logger.info("Collection updated", collection_id=collection.id, name=collection.name)
    
    return CollectionResponse.model_validate(collection)


@router.delete("/{collection_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a collection and all its documents"""
    
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Delete collection (cascades to documents and chunks)
    await db.delete(collection)
    await db.commit()
    
    logger.info("Collection deleted", collection_id=collection_id, name=collection.name)


# Articles endpoints for collections
@router.get("/{collection_id}/articles", response_model=List[dict])
async def get_collection_articles(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """Get all articles for a collection from database"""
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Get articles from database
    result = await db.execute(
        select(Article)
        .where(Article.collection_id == collection_id)
        .order_by(Article.created_at.desc())
    )
    articles = result.scalars().all()
    
    # Convert to frontend format
    articles_list = []
    for article in articles:
        articles_list.append({
            "id": article.id,
            "title": article.title,
            "topic": article.topic,
            "status": article.status.value,
            "word_count": article.word_count or 0,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat(),
            "writing_style": article.writing_style,
            "article_type": article.article_type,
            "target_length": article.target_length,
            "generation_time_seconds": article.generation_time_seconds,
            "model_used": article.model_used,
            "content": article.content_markdown,  # Include content for frontend
            "content_preview": (article.content_markdown or "")[:200] + "..." if article.content_markdown and len(article.content_markdown) > 200 else article.content_markdown or "",
            "has_outline": bool(article.outline_json),
            "has_content": bool(article.content_markdown)
        })
    
    return articles_list


# Documents endpoints for collections
@router.get("/{collection_id}/documents", response_model=dict)
async def get_collection_documents(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get all documents for a collection from database"""
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Get documents from database - only select core columns that exist
    result = await db.execute(
        select(
            KBDocument.id,
            KBDocument.collection_id,
            KBDocument.filename,
            KBDocument.original_filename,
            KBDocument.mime_type,
            KBDocument.size_bytes,
            KBDocument.file_path,
            KBDocument.status,
            KBDocument.chunk_count,
            KBDocument.created_at,
            KBDocument.updated_at
        )
        .where(KBDocument.collection_id == collection_id)
        .order_by(KBDocument.created_at.desc())
    )
    documents = result.all()
    
    # Convert to frontend format
    documents_list = []
    for doc in documents:
        documents_list.append({
            "id": doc.id,
            "collection_id": doc.collection_id,
            "filename": doc.filename,
            "original_filename": doc.original_filename or doc.filename,
            "mime_type": doc.mime_type,
            "size_bytes": doc.size_bytes or 0,
            "sha256": "",  # Not used in current schema but required by frontend
            "status": doc.status.value,
            "error_message": "",  # Not used but may be expected
            "chunk_count": doc.chunk_count or 0,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        })
    
    return {
        "documents": documents_list,
        "total": len(documents_list)
    }


@router.post("/{collection_id}/documents/", response_model=dict)
async def upload_document(
    collection_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Upload a single document to a collection"""
    
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # For now, use the batch upload system for single files
    # This ensures consistent processing pipeline
    try:
        from app.services.upload_manager import upload_manager
        import tempfile
        import shutil
        from pathlib import Path
        from datetime import datetime
        
        # Save uploaded file temporarily
        temp_dir = Path(tempfile.gettempdir()) / "single_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        job_temp_dir = temp_dir / f"single_{collection_id}_{int(datetime.now().timestamp())}"
        job_temp_dir.mkdir()
        
        file_path = job_temp_dir / file.filename
        
        try:
            # Save uploaded file
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            
            # Create upload job for single file using multiple_files type
            job_result = await upload_manager.create_upload_job(
                collection_id=collection_id,
                upload_type="multiple_files",
                file_paths=[str(file_path)],
                preserve_structure=False,
                skip_unsupported=True,
                max_file_size_mb=500,
                db=db
            )
            
            # Start processing in background
            job_id = job_result["job_id"]
            
            # Add background task to start processing
            background_tasks.add_task(
                _start_job_processing,
                job_id
            )
            
            # For now, return the job info and let frontend track progress
            return {
                "id": None,  # Will be set after processing
                "collection_id": collection_id,
                "filename": file.filename,
                "original_filename": file.filename,
                "mime_type": file.content_type,
                "size_bytes": 0,  # Will be calculated during processing
                "sha256": "",
                "status": "pending",
                "error_message": "",
                "chunk_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "job_id": job_id,
                "message": "File upload accepted. Processing started."
            }
            
        except Exception as e:
            # Cleanup temp files on error
            if job_temp_dir.exists():
                shutil.rmtree(job_temp_dir)
            raise e
            
    except Exception as e:
        logger.error(f"Single file upload failed: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get("/{collection_id}/documents/{document_id}", response_model=dict)
async def get_document(
    collection_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get a specific document by ID"""
    
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Get the specific document
    result = await db.execute(
        select(
            KBDocument.id,
            KBDocument.collection_id,
            KBDocument.filename,
            KBDocument.original_filename,
            KBDocument.mime_type,
            KBDocument.size_bytes,
            KBDocument.file_path,
            KBDocument.status,
            KBDocument.chunk_count,
            KBDocument.created_at,
            KBDocument.updated_at
        ).where(
            KBDocument.collection_id == collection_id,
            KBDocument.id == document_id
        )
    )
    document = result.first()
    
    if not document:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found in collection {collection_id}"
        )
    
    return {
        "id": document.id,
        "collection_id": document.collection_id,
        "filename": document.filename,
        "original_filename": document.original_filename or document.filename,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes or 0,
        "sha256": "",  # Not used in current schema but may be expected
        "status": document.status.value,
        "error_message": "",  # Not used but may be expected
        "chunk_count": document.chunk_count or 0,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat()
    }


@router.delete("/{collection_id}/documents/{document_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_document(
    collection_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a specific document"""
    
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Get the document to delete
    result = await db.execute(
        select(KBDocument).where(
            KBDocument.collection_id == collection_id,
            KBDocument.id == document_id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found in collection {collection_id}"
        )
    
    # Delete the document
    await db.delete(document)
    await db.commit()
    
    logger.info(f"Document {document_id} deleted from collection {collection_id}")


@router.get("/{collection_id}/documents/{document_id}/status", response_model=dict)
async def get_document_processing_status(
    collection_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get processing status for a specific document"""
    
    # Get the document 
    result = await db.execute(
        select(
            KBDocument.id,
            KBDocument.status,
            KBDocument.chunk_count,
            KBDocument.updated_at
        ).where(
            KBDocument.collection_id == collection_id,
            KBDocument.id == document_id
        )
    )
    document = result.first()
    
    if not document:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    
    return {
        "document_id": document.id,
        "status": document.status.value,
        "chunk_count": document.chunk_count or 0,
        "last_updated": document.updated_at.isoformat(),
        "progress": 100 if document.status.value == "completed" else 0
    }


@router.post("/{collection_id}/search/", response_model=dict)
async def search_documents(
    collection_id: int,
    search_request: SearchRequest,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Search for documents in a collection using semantic search"""

    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    try:
        # Initialize document processor
        doc_processor = DocumentProcessingPipeline()

        # Perform semantic search
        search_results = await doc_processor.search_similar_content(
            collection_id=collection_id,
            query_text=search_request.query,
            limit=limit,
            db=db
        )

        # Extract results from the search response
        results = search_results.get('matches', [])

        logger.info(f"Search completed for collection {collection_id}, query: '{search_request.query}', found {len(results)} results")

        return {
            "query": search_request.query,
            "collection_id": collection_id,
            "total_results": len(results),
            "results": results,
            "search_metadata": {
                "embedding_model": search_results.get('embedding_model'),
                "search_time_ms": search_results.get('search_time_ms', 0)
            }
        }

    except Exception as e:
        logger.error(f"Search failed for collection {collection_id}: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/{collection_id}/reprocess-documents", response_model=dict)
async def reprocess_collection_documents(
    collection_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Reprocess all documents in a collection to fix missing embeddings"""

    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )

    # Get all documents in the collection
    docs_result = await db.execute(
        select(KBDocument).where(KBDocument.collection_id == collection_id)
    )
    documents = docs_result.scalars().all()

    if not documents:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"No documents found in collection {collection_id}"
        )

    try:
        # Initialize document processor
        doc_processor = DocumentProcessingPipeline()

        # Reprocess each document
        reprocessed_count = 0
        for document in documents:
            try:
                logger.info(f"Reprocessing document {document.id}: {document.original_filename}")
                await doc_processor.reprocess_document(
                    document_id=document.id,
                    collection_id=collection_id,
                    file_path=document.file_path,
                    mime_type=document.mime_type
                )
                reprocessed_count += 1
            except Exception as e:
                logger.error(f"Failed to reprocess document {document.id}: {e}")

        # Update collection counters
        await _update_collection_counters(collection_id, db)

        logger.info(f"Reprocessed {reprocessed_count}/{len(documents)} documents in collection {collection_id}")

        return {
            "message": f"Reprocessing initiated for collection {collection_id}",
            "collection_id": collection_id,
            "total_documents": len(documents),
            "reprocessed_count": reprocessed_count
        }

    except Exception as e:
        logger.error(f"Reprocessing failed for collection {collection_id}: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Reprocessing failed: {str(e)}"
        )


async def _update_collection_counters(collection_id: int, db: AsyncSession):
    """Update collection document and chunk counters"""
    # Count documents
    docs_count_result = await db.execute(
        select(func.count(KBDocument.id)).where(KBDocument.collection_id == collection_id)
    )
    total_documents = docs_count_result.scalar() or 0

    # Count chunks
    chunks_count_result = await db.execute(
        select(func.sum(KBDocument.chunk_count)).where(KBDocument.collection_id == collection_id)
    )
    total_chunks = chunks_count_result.scalar() or 0

    # Update collection
    await db.execute(
        update(KBCollection).where(KBCollection.id == collection_id).values(
            total_documents=total_documents,
            total_chunks=total_chunks
        )
    )
    await db.commit()

    logger.info(f"Updated collection {collection_id} counters: {total_documents} docs, {total_chunks} chunks")


@router.post("/{collection_id}/generate-article")
async def generate_article_for_collection(
    collection_id: int,
    article_data: dict,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Generate a new article for a collection using real LLM"""
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    import time
    import asyncio
    article_id = int(time.time() * 1000) % 1000000  # Simple ID generation
    
    # Store the initial article in our temporary storage
    article = {
        "id": article_id,
        "collection_id": collection_id,
        "title": f"Article: {article_data.get('topic', 'Untitled')}",
        "topic": article_data.get("topic", ""),
        "status": "generating",
        "progress": "Starting article generation...",
        "content": None,
        "created_at": time.time(),
        "writing_style": article_data.get("writing_style", "professional"),
        "article_type": article_data.get("article_type", "comprehensive"),
        "target_length": article_data.get("target_length", "medium")
    }
    
    if collection_id not in generated_articles:
        generated_articles[collection_id] = {}
    generated_articles[collection_id][article_id] = article
    
    # Start real article generation in background
    asyncio.create_task(generate_article_content(collection_id, article_id, article_data))
    
    return {
        "id": article_id,
        "message": f"Article generation initiated for collection {collection_id}",
        "collection_name": collection.name,
        "status": "generating",
        "topic": article_data.get("topic", ""),
        "progress": 0
    }


@router.get("/{collection_id}/articles/{article_id}")
async def get_article(
    collection_id: int,
    article_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get a specific article from database"""
    # Verify collection exists
    result = await db.execute(
        select(KBCollection).where(KBCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Get article from database
    result = await db.execute(
        select(Article)
        .where(Article.id == article_id, Article.collection_id == collection_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Article with id {article_id} not found in collection {collection_id}"
        )
    
    # Return full article data
    return {
        "id": article.id,
        "title": article.title,
        "topic": article.topic,
        "status": article.status.value,
        "content": article.content_markdown,
        "word_count": article.word_count or 0,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat(),
        "writing_style": article.writing_style,
        "article_type": article.article_type,
        "target_length": article.target_length,
        "generation_time_seconds": article.generation_time_seconds,
        "model_used": article.model_used,
        "outline_json": article.outline_json,
        "has_outline": bool(article.outline_json),
        "has_content": bool(article.content_markdown)
    }