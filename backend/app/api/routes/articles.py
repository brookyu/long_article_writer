"""
Article generation API routes with streaming support
"""

import asyncio
import json
import logging
from typing import Dict, Any, AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.services.article_generator import ArticleGenerator
from app.services.ollama_client import OllamaClient
from app.services.document_processor import DocumentProcessingPipeline
from app.schemas.articles import ArticleRequest, ArticleResponse, OutlineRequest
from app.models.knowledge_base import KBCollection, Article, ArticleStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
ollama_client = OllamaClient()
doc_processor = DocumentProcessingPipeline()

async def get_article_generator(db: AsyncSession) -> ArticleGenerator:
    """Get article generator with dependencies"""
    
    # Create a wrapper function that includes the database session
    async def llm_function_with_db(prompt: str, max_tokens: int = 1000) -> str:
        # Auto-detect refinement tasks based on prompt content
        is_refinement = any(keyword in prompt.lower() for keyword in ['refine', 'refinement', 'feedback', 'improve'])
        return await ollama_client.generate_text(prompt, model=None, max_tokens=max_tokens, db=db, is_refinement=is_refinement)
    
    # Create a search function wrapper that includes the database session
    async def search_function_with_db(collection_id: int, query: str, limit: int = 10) -> Dict[str, Any]:
        return await doc_processor.search_similar_content(
            collection_id=collection_id,
            query_text=query,
            limit=limit,
            db=db
        )
    
    return ArticleGenerator(
        llm_function=llm_function_with_db,
        search_function=search_function_with_db
    )


async def save_article_to_db(
    db: AsyncSession,
    topic: str,
    collection_id: int,
    article_type: str = "comprehensive",
    target_length: str = "medium",
    writing_style: str = "professional"
) -> Article:
    """Save a new article to the database"""
    
    article = Article(
        title=f"Article: {topic}",
        topic=topic,
        collection_id=collection_id,
        status=ArticleStatus.OUTLINING,
        article_type=article_type,
        target_length=target_length,
        writing_style=writing_style
    )
    
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


async def update_article_in_db(
    db: AsyncSession,
    article: Article,
    **updates
) -> Article:
    """Update an existing article in the database"""
    
    for key, value in updates.items():
        if hasattr(article, key):
            setattr(article, key, value)
    
    await db.commit()
    await db.refresh(article)
    return article


@router.post("/outline")
async def generate_outline_stream(
    request: OutlineRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate article outline with streaming response"""
    
    # Verify collection exists
    result = await db.execute(select(KBCollection).where(KBCollection.id == request.collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    async def stream_outline():
        article = None
        try:
            # Save initial article to database
            article = await save_article_to_db(
                db, 
                request.topic, 
                request.collection_id, 
                request.article_type,
                request.target_length
            )
            
            generator = await get_article_generator(db)
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting research...', 'step': 1, 'total_steps': 3})}\n\n"
            
            # Step 1: Research
            research_results = await generator.researcher.research_topic(
                request.collection_id, request.topic, request.subtopics
            )
            
            yield f"data: {json.dumps({'type': 'research', 'data': research_results})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Research complete. Generating outline...', 'step': 2, 'total_steps': 3})}\n\n"
            
            # Create research summary
            research_summary = f"""
Research Summary for "{request.topic}":
- Total relevant chunks found: {research_results['total_chunks_found']}
- Documents consulted: {len(research_results['unique_documents'])}
- Search queries used: {', '.join(research_results['search_queries_used'])}

Key findings from research:
"""
            
            for research_key, research_info in research_results["research_data"].items():
                top_result = research_info["results"][0] if research_info["results"] else None
                if top_result:
                    research_summary += f"- {research_info['query']}: {top_result.get('preview', '')[:100]}...\n"
            
            # Step 2: Generate outline
            outline_result = await generator.outline_generator.generate_outline(
                request.topic, research_summary, request.article_type, request.target_length
            )
            
            # Update article with outline and status
            article = await update_article_in_db(
                db,
                article,
                outline_json=json.dumps(outline_result),
                status=ArticleStatus.COMPLETED,
                title=outline_result.get('topic', f"Article: {request.topic}")
            )
            
            # Include article ID in the response
            enhanced_outline_result = {
                **outline_result,
                "article_id": article.id,
                "saved_to_db": True
            }
            
            yield f"data: {json.dumps({'type': 'outline', 'data': enhanced_outline_result})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Outline complete and saved!', 'step': 3, 'total_steps': 3})}\n\n"
            
            # Final completion
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Outline generation completed successfully', 'article_id': article.id})}\n\n"
            
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            # Mark article as failed if it was created
            if article:
                try:
                    await update_article_in_db(db, article, status=ArticleStatus.OUTLINING)
                except:
                    pass
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_outline(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/collection/{collection_id}")
async def get_collection_articles(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all articles for a collection"""
    
    # Verify collection exists
    result = await db.execute(select(KBCollection).where(KBCollection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get articles for this collection
    result = await db.execute(
        select(Article)
        .where(Article.collection_id == collection_id)
        .order_by(Article.created_at.desc())
    )
    articles = result.scalars().all()
    
    # Convert to response format
    articles_data = []
    for article in articles:
        articles_data.append({
            "id": article.id,
            "title": article.title,
            "topic": article.topic,
            "status": article.status.value,
            "word_count": article.word_count or 0,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat(),
            "article_type": article.article_type,
            "target_length": article.target_length,
            "writing_style": article.writing_style,
            "model_used": article.model_used,
            "generation_time_seconds": article.generation_time_seconds,
            "content_preview": (article.content_markdown or "")[:200] + "..." if article.content_markdown and len(article.content_markdown) > 200 else article.content_markdown or "",
            "has_outline": bool(article.outline_json),
            "has_content": bool(article.content_markdown)
        })
    
    return {
        "collection_id": collection_id,
        "collection_name": collection.name,
        "articles": articles_data,
        "total": len(articles_data)
    }


@router.post("/draft")
async def generate_draft_stream(
    request: ArticleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate article draft with streaming response"""
    
    # Verify collection exists
    result = await db.execute(select(KBCollection).where(KBCollection.id == request.collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    async def stream_draft():
        try:
            generator = await get_article_generator(db)
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting article generation...', 'step': 1, 'total_steps': 5})}\n\n"
            
            # Step 1: Research
            research_results = await generator.researcher.research_topic(
                request.collection_id, request.topic, request.subtopics
            )
            
            yield f"data: {json.dumps({'type': 'research', 'data': research_results})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Research complete. Generating outline...', 'step': 2, 'total_steps': 5})}\n\n"
            
            # Create research summary
            research_summary = f"""
Research Summary for "{request.topic}":
- Total relevant chunks found: {research_results['total_chunks_found']}
- Documents consulted: {len(research_results['unique_documents'])}
- Search queries used: {', '.join(research_results['search_queries_used'])}

Key findings from research:
"""
            
            for research_key, research_info in research_results["research_data"].items():
                top_result = research_info["results"][0] if research_info["results"] else None
                if top_result:
                    research_summary += f"- {research_info['query']}: {top_result.get('preview', '')[:100]}...\n"
            
            # Step 2: Generate outline
            outline_result = await generator.outline_generator.generate_outline(
                request.topic, research_summary, request.article_type, request.target_length
            )
            
            yield f"data: {json.dumps({'type': 'outline', 'data': outline_result})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Outline complete. Generating content...', 'step': 3, 'total_steps': 5})}\n\n"
            
            # Step 3: Start article content
            article_lines = outline_result["outline_text"].split('\n')
            title = next((line[2:].strip() for line in article_lines if line.startswith('# ')), request.topic)
            
            yield f"data: {json.dumps({'type': 'title', 'data': title})}\n\n"
            title_content = f"# {title}\n\n"
            yield f"data: {json.dumps({'type': 'content', 'data': title_content})}\n\n"
            
            # Step 4: Generate content for each section
            sections = outline_result.get("sections", [])
            total_sections = len(sections)
            
            for i, section in enumerate(sections):
                section_title = section.get("title", "")
                section_context = f"Section about {section_title} in an article about {request.topic}"
                
                yield f"data: {json.dumps({'type': 'status', 'message': f'Generating section: {section_title}', 'step': 4, 'total_steps': 5, 'section': i+1, 'total_sections': total_sections})}\n\n"
                
                # Stream section header
                section_header = f"## {section_title}\n\n"
                yield f"data: {json.dumps({'type': 'content', 'data': section_header})}\n\n"
                
                # Generate section content
                section_content = await generator.content_generator.generate_section(
                    request.collection_id,
                    section_title,
                    section_context,
                    research_results,
                    request.writing_style
                )
                
                # Stream section content
                section_content_formatted = f"{section_content}\n\n"
                yield f"data: {json.dumps({'type': 'content', 'data': section_content_formatted})}\n\n"
            
            # Step 5: Completion
            yield f"data: {json.dumps({'type': 'status', 'message': 'Article generation complete!', 'step': 5, 'total_steps': 5})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Article generated successfully'})}\n\n"
            
        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_draft(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/refine")
async def refine_section_stream(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Refine a specific section with streaming response"""
    
    collection_id = request.get("collection_id")
    section_title = request.get("section_title")
    current_content = request.get("current_content")
    refinement_instructions = request.get("instructions")
    
    if not all([collection_id, section_title, current_content, refinement_instructions]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Verify collection exists
    collection = db.query(KBCollection).filter(KBCollection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    async def stream_refinement():
        try:
            generator = await get_article_generator(db)
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'Refining section: {section_title}...'})}\n\n"
            
            # Create refinement prompt
            prompt = f"""Please refine the following section based on the user's instructions:

Section Title: {section_title}
Current Content:
{current_content}

Refinement Instructions:
{refinement_instructions}

Please provide an improved version that addresses the feedback while maintaining the original structure and flow."""
            
            refined_content = await ollama_client.generate_text(prompt, max_tokens=800)
            
            yield f"data: {json.dumps({'type': 'refined_content', 'data': refined_content})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Section refinement complete'})}\n\n"
            
        except Exception as e:
            logger.error(f"Section refinement failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_refinement(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/export")
async def export_article(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Export article as markdown with front-matter"""
    
    title = request.get("title", "Untitled Article")
    content = request.get("content", "")
    topic = request.get("topic", "")
    collection_id = request.get("collection_id")
    
    if not content:
        raise HTTPException(status_code=400, detail="No content to export")
    
    # Generate front-matter
    front_matter = f"""---
title: "{title}"
topic: "{topic}"
collection_id: {collection_id}
generated_at: "{datetime.now().isoformat()}"
generator: "Long Article Writer"
---

"""
    
    # Combine front-matter with content
    markdown_content = front_matter + content
    
    # In a real implementation, you'd save this to a file and return a download link
    # For now, we'll return the content directly
    
    return {
        "status": "success",
        "markdown": markdown_content,
        "filename": f"{title.replace(' ', '_').lower()}.md",
        "download_url": f"/api/articles/download/{title.replace(' ', '_').lower()}.md"
    }


@router.post("/{collection_id}/generate-outline-stream")
async def generate_outline_stream_by_collection(
    collection_id: int,
    request: OutlineRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate article outline with streaming response for a specific collection"""
    
    # Set the collection_id from URL parameter
    request.collection_id = collection_id
    
    # Verify collection exists
    result = await db.execute(select(KBCollection).where(KBCollection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    async def stream_outline():
        print("🎬 STREAM_OUTLINE GENERATOR STARTED")
        logger.info("🎬 Starting stream_outline generator")
        article = None
        try:
            # Save initial article to database
            article = await save_article_to_db(
                db, 
                request.topic, 
                collection_id, 
                request.article_type,
                request.target_length
            )
            
            logger.info("📝 Creating article generator...")
            generator = await get_article_generator(db)
            logger.info("📝 Article generator created successfully")
            
            # Send initial status
            yield f"data: {{\"type\": \"status\", \"message\": \"Starting research...\", \"step\": 1, \"total_steps\": 3}}\n\n"
            
            # Step 1: Research
            logger.info(f"📝 Starting research for topic: {request.topic}")
            research_results = await generator.researcher.research_topic(
                collection_id, request.topic, request.subtopics
            )
            logger.info(f"📝 Research completed with {research_results['total_chunks_found']} chunks")
            
            # Determine source type for clearer messaging
            source_type = research_results.get('source_type', 'local_knowledge_base')
            local_docs = len(research_results['unique_documents'])
            web_results = len(research_results.get('web_search_results', []))
            
            yield f"data: {{\"type\": \"research_complete\", \"chunks_found\": {research_results['total_chunks_found']}, \"documents_searched\": {local_docs}, \"web_results\": {web_results}, \"source_type\": \"{source_type}\"}}\n\n"
            
            # Create research summary with clear source attribution
            if source_type == 'web_search':
                research_summary = f"""
Research Summary for "{request.topic}":
- Source: Web Search (local knowledge base unavailable)
- Web search results: {web_results}
- Local documents: {local_docs}
- Search queries used: {', '.join(research_results['search_queries_used'])}

Key findings from web search:
"""
                # Add web search results
                if research_results.get('web_search_results'):
                    for result in research_results['web_search_results'][:3]:
                        research_summary += f"- {result['title']}: {result['snippet'][:100]}...\n"
                        research_summary += f"  Source: {result['url']}\n"
            else:
                research_summary = f"""
Research Summary for "{request.topic}":
- Source: Local Knowledge Base
- Total relevant chunks found: {research_results['total_chunks_found']}
- Documents consulted: {local_docs}
- Search queries used: {', '.join(research_results['search_queries_used'])}

Key findings from research:
{chr(10).join([f"- {chunk['text'][:100]}..." for chunk in research_results.get('research_chunks', [])[:5]])}
"""
            
            # Step 2: Generate outline
            yield f"data: {{\"type\": \"status\", \"message\": \"Generating outline...\", \"step\": 2, \"total_steps\": 3}}\n\n"
            
            outline = await generator.outline_generator.generate_outline(
                request.topic, research_summary, request.article_type, request.target_length
            )
            
            # Update article with outline
            if article:
                article.outline_json = json.dumps(outline) if not isinstance(outline, str) else outline
                article.status = ArticleStatus.DRAFTING
                await db.commit()
            
            yield f"data: {{\"type\": \"outline\", \"outline\": {json.dumps(outline)}, \"article_id\": {article.id if article else None}}}\n\n"
            yield f"data: {{\"type\": \"status\", \"message\": \"Outline complete!\", \"step\": 3, \"total_steps\": 3}}\n\n"
            
        except Exception as e:
            logger.error(f"Error generating outline: {str(e)}")
            yield f"data: {{\"type\": \"error\", \"message\": \"Error generating outline: {str(e)}\"}}\n\n"
            
            # Update article status to failed
            if article:
                article.status = ArticleStatus.OUTLINING
                await db.commit()
    
    return StreamingResponse(
        stream_outline(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.post("/{collection_id}/{article_id}/refine-outline-stream")
async def refine_outline_stream(
    collection_id: int,
    article_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Refine article outline based on user feedback with streaming response"""
    
    refinement_instructions = request.get("refinement_instructions", "")
    if not refinement_instructions:
        raise HTTPException(status_code=400, detail="Refinement instructions are required")
    
    # Get the existing article
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    async def generate_refined_outline():
        try:
            # Update article status
            article.status = ArticleStatus.OUTLINING
            await db.commit()
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Refining outline...'})}\n\n"
            
            # Get article generator with database context
            generator = await get_article_generator(db)
            
            # Refine the outline with feedback
            refined_outline = await generator.refine_outline(
                original_outline=article.outline_json,
                topic=article.topic,
                refinement_instructions=refinement_instructions,
                collection_id=collection_id
            )
            
            # Update article with refined outline
            article.outline_json = json.dumps(refined_outline) if isinstance(refined_outline, dict) else refined_outline
            article.status = ArticleStatus.OUTLINING
            await db.commit()
            
            yield f"data: {json.dumps({'type': 'outline', 'outline': refined_outline, 'article_id': article_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Error refining outline: {e}")
            article.status = ArticleStatus.OUTLINING if article else None
            if article:
                await db.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_refined_outline(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/{collection_id}/{article_id}/generate-content-stream")
async def generate_content_stream(
    collection_id: int,
    article_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Generate article content from approved outline with streaming response"""
    
    feedback = request.get("feedback", "")
    
    # Get the existing article
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if not article.outline_json:
        raise HTTPException(status_code=400, detail="Article outline not found")
    
    async def generate_content():
        try:
            # Update article status
            article.status = ArticleStatus.DRAFTING
            await db.commit()
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating content...'})}\n\n"
            
            # Get article generator with database context
            generator = await get_article_generator(db)
            
            # Parse outline
            try:
                outline = json.loads(article.outline_json) if isinstance(article.outline_json, str) else article.outline_json
            except json.JSONDecodeError:
                outline = article.outline_json
            
            # Generate content with feedback
            content = await generator.generate_content(
                outline=outline,
                topic=article.topic,
                collection_id=collection_id,
                content_feedback=feedback
            )
            
            # Update article with generated content
            article.content_markdown = content
            article.status = ArticleStatus.COMPLETED
            article.word_count = len(content.split()) if content else 0
            await db.commit()
            
            yield f"data: {json.dumps({'type': 'content', 'content': content, 'article_id': article_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            article.status = ArticleStatus.OUTLINING if article else None
            if article:
                await db.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_content(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/{collection_id}/{article_id}/refine-content-stream")
async def refine_content_stream(
    collection_id: int,
    article_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Refine article content based on user feedback with streaming response"""
    
    refinement_instructions = request.get("refinement_instructions", "")
    if not refinement_instructions:
        raise HTTPException(status_code=400, detail="Refinement instructions are required")
    
    # Get the existing article
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if not article.content_markdown:
        raise HTTPException(status_code=400, detail="Article content not found")
    
    async def generate_refined_content():
        try:
            # Update article status
            article.status = ArticleStatus.REFINING
            await db.commit()
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Refining content...'})}\n\n"
            
            # Get article generator with database context
            generator = await get_article_generator(db)
            
            # Refine the content with feedback
            refined_content = await generator.refine_content(
                original_content=article.content_markdown,
                topic=article.topic,
                refinement_instructions=refinement_instructions,
                collection_id=collection_id
            )
            
            # Update article with refined content
            article.content_markdown = refined_content
            article.status = ArticleStatus.COMPLETED
            article.word_count = len(refined_content.split()) if refined_content else 0
            await db.commit()
            
            yield f"data: {json.dumps({'type': 'content', 'content': refined_content, 'article_id': article_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Error refining content: {e}")
            article.status = ArticleStatus.OUTLINING if article else None
            if article:
                await db.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_refined_content(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )