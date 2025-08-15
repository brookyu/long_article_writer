"""
Collection management endpoints
"""

from typing import List
from http import HTTPStatus
import time
import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.knowledge_base import KBCollection
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

logger = structlog.get_logger(__name__)
router = APIRouter()

# Temporary in-memory storage for generated articles
# In a real implementation, this would be stored in the database
generated_articles = {}


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
    
    # Create new collection
    new_collection = KBCollection(
        name=collection_data.name,
        description=collection_data.description,
        embedding_model=collection_data.embedding_model
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
    
    collection_responses = [CollectionResponse.model_validate(col) for col in collections]
    
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
    """Get all articles for a collection"""
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
    
    # Return articles from our temporary storage
    if collection_id not in generated_articles:
        return []
    
    articles_list = []
    for article_id, article in generated_articles[collection_id].items():
        # Return summary info for list view (no simulation needed)
        articles_list.append({
            "id": article["id"],
            "title": article["title"],
            "topic": article["topic"],
            "status": article["status"],
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(article["created_at"])),
            "writing_style": article["writing_style"],
            "article_type": article["article_type"]
        })
    
    # Sort by creation time (newest first)
    articles_list.sort(key=lambda x: x["id"], reverse=True)
    return articles_list


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
    """Get a specific article"""
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
    
    # Check if article exists in our temporary storage
    if collection_id not in generated_articles or article_id not in generated_articles[collection_id]:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Article with id {article_id} not found in collection {collection_id}"
        )
    
    article = generated_articles[collection_id][article_id]
    
    # Article content is now generated by the real LLM process
    # No need for simulation - just return the current state
    
    return article