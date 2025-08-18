"""
Enhanced API routes for Pydantic AI agent-based article generation
with section-by-section feedback loops
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.services.simplified_enhanced_agents import (
    SimplifiedAgentOrchestrator,
    GenerationPhase,
    FeedbackType,
    SectionFeedback,
    ArticleFeedback,
    GenerationState
)
from app.services.ollama_client import OllamaClient
from app.services.document_processor import DocumentProcessingPipeline
from app.services.web_search import WebSearchManager
from app.models.knowledge_base import KBCollection, Article, ArticleStatus
from app.schemas.articles import ArticleRequest, OutlineRequest

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize services
ollama_client = OllamaClient()
doc_processor = DocumentProcessingPipeline()

# Global orchestrator instances (in production, use proper session management)
orchestrators: Dict[int, SimplifiedAgentOrchestrator] = {}


class GenerationRequest(BaseModel):
    """Request to start article generation"""
    topic: str
    article_type: str = "comprehensive"
    target_length: str = "medium"
    writing_style: str = "professional"
    user_preferences: Dict[str, Any] = {}


class SectionFeedbackRequest(BaseModel):
    """Request to provide feedback on a section"""
    feedback_type: FeedbackType
    feedback_text: str
    specific_changes: Optional[str] = None
    priority: str = "medium"


class ArticleFeedbackRequest(BaseModel):
    """Request to provide feedback on the complete article"""
    feedback_type: FeedbackType
    feedback_text: str
    section_feedback: List[Dict[str, Any]] = []
    overall_suggestions: List[str] = []
    priority: str = "medium"


async def get_orchestrator(collection_id: int, db: AsyncSession) -> SimplifiedAgentOrchestrator:
    """Get or create orchestrator for collection"""
    if collection_id not in orchestrators:
        # Create LLM function wrapper
        async def llm_function_with_db(prompt: str, max_tokens: int = 1000, is_refinement: bool = False) -> str:
            return await ollama_client.generate_text(prompt, model=None, max_tokens=max_tokens, db=db, is_refinement=is_refinement)
        
        # Create web search function
        try:
            web_search_manager = WebSearchManager()
            async def web_search_function(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
                results = await web_search_manager.search(query, max_results)
                return [result.to_dict() for result in results] if results else []
        except Exception as e:
            logger.warning(f"Web search not available: {e}")
            web_search_function = None
        
        # Create a search function wrapper that includes the database session
        async def search_function_with_db(collection_id: int, query: str, limit: int = 10) -> Dict[str, Any]:
            return await doc_processor.search_similar_content(
                collection_id=collection_id,
                query_text=query,
                limit=limit,
                db=db
            )
        
        # Create orchestrator
        orchestrators[collection_id] = SimplifiedAgentOrchestrator(
            collection_id=collection_id,
            search_function=search_function_with_db,
            llm_function=llm_function_with_db,
            web_search_function=web_search_function
        )
    
    return orchestrators[collection_id]


@router.post("/{collection_id}/start-generation")
async def start_article_generation(
    collection_id: int,
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a new article generation session with enhanced agents"""
    
    # Verify collection exists
    result = await db.execute(select(KBCollection).where(KBCollection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        # Start generation session
        session_result = await orchestrator.start_article_generation(
            topic=request.topic,
            article_type=request.article_type,
            target_length=request.target_length,
            writing_style=request.writing_style,
            user_preferences=request.user_preferences
        )
        
        logger.info(f"🚀 Started enhanced generation session: {session_result['session_id']}")
        
        return {
            "status": "success",
            "session_id": session_result["session_id"],
            "current_phase": session_result["current_phase"],
            "message": session_result["message"],
            "next_action": "process_research"
        }
        
    except Exception as e:
        logger.error(f"Failed to start generation: {e}")
        raise HTTPException(status_code=500, detail=f"Generation start failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/research")
async def process_research_phase(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Process the research phase"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        research_result = await orchestrator.process_research_phase(session_id)
        
        return {
            "status": "success",
            "phase": "research",
            "data": research_result,
            "next_action": "generate_outline"
        }
        
    except Exception as e:
        logger.error(f"Research phase failed: {e}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/outline")
async def generate_outline(
    collection_id: int,
    session_id: str,
    research_feedback: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Generate article outline"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        outline_result = await orchestrator.generate_outline(session_id, research_feedback)
        
        return {
            "status": "success",
            "phase": "outline",
            "outline": outline_result["outline"],
            "requires_feedback": outline_result["requires_feedback"],
            "next_action": "provide_outline_feedback_or_start_sections"
        }
        
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Outline generation failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/sections/{section_id}/generate")
async def generate_section(
    collection_id: int,
    session_id: str,
    section_id: str,
    section_feedback: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Generate content for a specific section"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        section_result = await orchestrator.generate_section(
            session_id, 
            section_id, 
            section_feedback
        )
        
        return {
            "status": "success",
            "phase": "section_generation",
            "section_id": section_id,
            "section_content": section_result["section_content"],
            "requires_feedback": section_result["requires_feedback"],
            "next_action": "provide_section_feedback"
        }
        
    except Exception as e:
        logger.error(f"Section generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Section generation failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/sections/{section_id}/feedback")
async def provide_section_feedback(
    collection_id: int,
    session_id: str,
    section_id: str,
    feedback_request: SectionFeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Provide feedback on a specific section"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        # Create feedback object
        feedback = SectionFeedback(
            section_id=section_id,
            feedback_type=feedback_request.feedback_type,
            feedback_text=feedback_request.feedback_text,
            specific_changes=feedback_request.specific_changes,
            priority=feedback_request.priority
        )
        
        feedback_result = await orchestrator.process_section_feedback(
            session_id, 
            section_id, 
            feedback
        )
        
        return {
            "status": "success",
            "section_id": section_id,
            "feedback_result": feedback_result,
            "next_action": "continue_refinement" if feedback_result.get("in_refinement_mode") else "move_to_next_section"
        }
        
    except Exception as e:
        logger.error(f"Section feedback processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback processing failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/move-to-next")
async def move_to_next_section(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Move to the next section in the workflow"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        move_result = await orchestrator.move_to_next_section(session_id)
        
        return {
            "status": "success",
            "move_result": move_result,
            "next_action": move_result.get("action_needed", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Move to next section failed: {e}")
        raise HTTPException(status_code=500, detail=f"Move to next failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/refine-final")
async def refine_final_article(
    collection_id: int,
    session_id: str,
    feedback: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Refine the final complete article"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        refinement_result = await orchestrator.refine_final_article(session_id, feedback)
        
        return {
            "status": "success",
            "refinement_result": refinement_result,
            "next_action": "final_review_continue"
        }
        
    except Exception as e:
        logger.error(f"Final article refinement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Final refinement failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/complete")
async def complete_article(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mark article as completed and prepare for download"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        completion_result = await orchestrator.complete_article(session_id)
        
        # Save to database if needed
        if completion_result.get("download_ready"):
            article = Article(
                title=completion_result["article_metadata"]["title"],
                topic=completion_result["article_metadata"]["topic"],
                collection_id=collection_id,
                content_markdown=completion_result["final_article"],
                status=ArticleStatus.COMPLETED,
                word_count=completion_result["article_metadata"]["total_words"],
                source_count=0,
                local_source_ratio=1.0,
                writing_style="professional",
                article_type="comprehensive",
                target_length="medium",
                model_used=await ollama_client.get_user_llm_model(db)
            )
            
            db.add(article)
            await db.commit()
            await db.refresh(article)
            
            completion_result["article_id"] = article.id
        
        return {
            "status": "success",
            "completion_result": completion_result,
            "next_action": "download_ready"
        }
        
    except Exception as e:
        logger.error(f"Article completion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Completion failed: {str(e)}")


@router.get("/{collection_id}/sessions/{session_id}/download")
async def download_article(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download the completed article as markdown"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        status = orchestrator.get_generation_status(session_id)
        state = orchestrator.active_generations.get(session_id)
        
        if not state or not state.final_article:
            raise HTTPException(status_code=404, detail="Article not ready for download")
        
        # Create filename
        safe_topic = "".join(c for c in state.topic if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_topic.replace(' ', '_')}.md"
        
        from fastapi.responses import Response
        
        return Response(
            content=state.final_article,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/markdown; charset=utf-8"
            }
        )
        
    except Exception as e:
        logger.error(f"Article download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/finalize")
async def finalize_article(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Finalize the complete article"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        finalization_result = await orchestrator.finalize_article(session_id)
        
        if finalization_result["status"] == "completed":
            # Save to database
            article = Article(
                title=f"Article: {finalization_result.get('topic', 'Generated Article')}",
                topic=finalization_result.get('topic', 'Generated Article'),
                collection_id=collection_id,
                content_markdown=finalization_result["final_article"],
                status=ArticleStatus.COMPLETED,
                word_count=finalization_result["total_words"],
                source_count=0,  # Could be calculated from sections
                local_source_ratio=1.0,  # Could be calculated
                writing_style="professional",  # From generation request
                article_type="comprehensive",  # From generation request
                target_length="medium",  # From generation request
                model_used=await ollama_client.get_user_llm_model(db)
            )
            
            db.add(article)
            await db.commit()
            await db.refresh(article)
            
            finalization_result["article_id"] = article.id
        
        return {
            "status": "success",
            "finalization_result": finalization_result,
            "next_action": "provide_final_feedback" if finalization_result["requires_final_feedback"] else "completed"
        }
        
    except Exception as e:
        logger.error(f"Article finalization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Finalization failed: {str(e)}")


@router.post("/{collection_id}/sessions/{session_id}/final-feedback")
async def provide_final_feedback(
    collection_id: int,
    session_id: str,
    feedback_request: ArticleFeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Provide final feedback on the complete article"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        # Create feedback object
        section_feedbacks = []
        for sf in feedback_request.section_feedback:
            section_feedback = SectionFeedback(
                section_id=sf["section_id"],
                feedback_type=FeedbackType(sf["feedback_type"]),
                feedback_text=sf["feedback_text"],
                specific_changes=sf.get("specific_changes"),
                priority=sf.get("priority", "medium")
            )
            section_feedbacks.append(section_feedback)
        
        feedback = ArticleFeedback(
            feedback_type=feedback_request.feedback_type,
            feedback_text=feedback_request.feedback_text,
            section_feedback=section_feedbacks,
            overall_suggestions=feedback_request.overall_suggestions,
            priority=feedback_request.priority
        )
        
        feedback_result = await orchestrator.process_final_feedback(session_id, feedback)
        
        return {
            "status": "success",
            "feedback_result": feedback_result,
            "next_action": "completed" if feedback_result["status"] == "completed" else "review_refinements"
        }
        
    except Exception as e:
        logger.error(f"Final feedback processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Final feedback processing failed: {str(e)}")


@router.get("/{collection_id}/sessions/{session_id}/status")
async def get_generation_status(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current status of article generation"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        status = orchestrator.get_generation_status(session_id)
        
        return {
            "status": "success",
            "generation_status": status
        }
        
    except Exception as e:
        logger.error(f"Status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@router.delete("/{collection_id}/sessions/{session_id}")
async def cleanup_session(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Clean up a completed generation session"""
    try:
        orchestrator = await get_orchestrator(collection_id, db)
        
        orchestrator.cleanup_session(session_id)
        
        return {
            "status": "success",
            "message": f"Session {session_id} cleaned up successfully"
        }
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session cleanup failed: {str(e)}")


# Streaming endpoints for real-time updates
@router.post("/{collection_id}/sessions/{session_id}/stream")
async def stream_generation_process(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stream the complete generation process with real-time updates"""
    
    async def stream_generation():
        try:
            orchestrator = await get_orchestrator(collection_id, db)
            
            # Stream research phase
            yield f"data: {json.dumps({'type': 'phase_start', 'phase': 'research', 'message': 'Starting research...'})}\n\n"
            
            research_result = await orchestrator.process_research_phase(session_id)
            yield f"data: {json.dumps({'type': 'phase_complete', 'phase': 'research', 'data': research_result})}\n\n"
            
            # Stream outline generation
            yield f"data: {json.dumps({'type': 'phase_start', 'phase': 'outline', 'message': 'Generating outline...'})}\n\n"
            
            outline_result = await orchestrator.generate_outline(session_id)
            yield f"data: {json.dumps({'type': 'phase_complete', 'phase': 'outline', 'data': outline_result, 'requires_feedback': True})}\n\n"
            
            # Wait for outline approval (this would be handled by the frontend)
            yield f"data: {json.dumps({'type': 'waiting_feedback', 'phase': 'outline', 'message': 'Waiting for outline approval...'})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_generation(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/{collection_id}/sessions/{session_id}/sections/stream")
async def stream_section_generation(
    collection_id: int,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stream section-by-section generation"""
    
    async def stream_sections():
        try:
            orchestrator = await get_orchestrator(collection_id, db)
            
            # Get generation state to determine sections
            status = orchestrator.get_generation_status(session_id)
            state = orchestrator.active_generations.get(session_id)
            
            if not state or not state.outline:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No outline available'})}\n\n"
                return
            
            # Generate each section
            for i, section in enumerate(state.outline.sections):
                section_id = section.get('id', f'section_{i}')
                section_title = section.get('title', f'Section {i+1}')
                
                yield f"data: {json.dumps({'type': 'section_start', 'section_id': section_id, 'title': section_title, 'message': f'Generating section: {section_title}'})}\n\n"
                
                section_result = await orchestrator.generate_section(session_id, section_id)
                
                yield f"data: {json.dumps({'type': 'section_complete', 'section_id': section_id, 'data': section_result, 'requires_feedback': True})}\n\n"
                
                # Wait for section approval
                yield f"data: {json.dumps({'type': 'waiting_feedback', 'section_id': section_id, 'message': f'Waiting for feedback on: {section_title}'})}\n\n"
            
            # All sections generated
            yield f"data: {json.dumps({'type': 'all_sections_complete', 'message': 'All sections generated, ready for finalization'})}\n\n"
            
        except Exception as e:
            logger.error(f"Section streaming failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_sections(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )