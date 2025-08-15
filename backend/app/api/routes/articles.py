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
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.article_generator import ArticleGenerator
from app.services.ollama_client import OllamaClient
from app.services.document_processor import DocumentProcessingPipeline
from app.schemas.articles import ArticleRequest, ArticleResponse, OutlineRequest
from app.models.knowledge_base import KBCollection

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
ollama_client = OllamaClient()
doc_processor = DocumentProcessingPipeline()

async def get_article_generator() -> ArticleGenerator:
    """Get article generator with dependencies"""
    return ArticleGenerator(
        llm_function=ollama_client.generate_text,
        search_function=doc_processor.search_similar_content
    )


@router.post("/outline")
async def generate_outline_stream(
    request: OutlineRequest,
    db: Session = Depends(get_db)
):
    """Generate article outline with streaming response"""
    
    # Verify collection exists
    collection = db.query(KBCollection).filter(KBCollection.id == request.collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    async def stream_outline():
        try:
            generator = await get_article_generator()
            
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
            
            yield f"data: {json.dumps({'type': 'outline', 'data': outline_result})}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': 'Outline complete!', 'step': 3, 'total_steps': 3})}\n\n"
            
            # Final completion
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Outline generation completed successfully'})}\n\n"
            
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
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


@router.post("/draft")
async def generate_draft_stream(
    request: ArticleRequest,
    db: Session = Depends(get_db)
):
    """Generate article draft with streaming response"""
    
    # Verify collection exists
    collection = db.query(KBCollection).filter(KBCollection.id == request.collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    async def stream_draft():
        try:
            generator = await get_article_generator()
            
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
    db: Session = Depends(get_db)
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
            generator = await get_article_generator()
            
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
    db: Session = Depends(get_db)
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