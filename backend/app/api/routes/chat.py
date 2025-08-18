"""
Chat-based article generation API endpoints with streaming support
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.pydantic_agents_simple import PydanticAgentOrchestrator, AgentResponse
from app.services.vector_store import MilvusVectorStore
from app.services.ollama_client import OllamaClient
from app.services.article_generator import ArticleGenerator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message from user"""
    content: str
    message_type: str = "user"  # user, system, agent
    context: Optional[Dict[str, Any]] = None


class ChatSessionRequest(BaseModel):
    """Chat session initiation request"""
    collection_id: int
    initial_message: ChatMessage
    user_preferences: Optional[Dict[str, Any]] = None


class OutlineRefinementRequest(BaseModel):
    """Request for outline refinement"""
    collection_id: int
    current_outline: Dict[str, Any]
    user_feedback: str
    session_id: str


class ResearchRequest(BaseModel):
    """Request for additional research"""
    collection_id: int
    topic: str
    specific_queries: List[str]
    session_id: str


class StreamEvent(BaseModel):
    """Streaming event"""
    event_type: str
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: Optional[str] = None


# In-memory session storage (in production, use Redis or database)
chat_sessions: Dict[str, Dict[str, Any]] = {}


def get_vector_store():
    """Get vector store instance"""
    return MilvusVectorStore()


def get_ollama_client():
    """Get Ollama client instance"""
    return OllamaClient()


async def create_chat_session(session_id: str, collection_id: int) -> str:
    """Create a new chat session"""
    
    # Initialize dependencies
    vector_store = get_vector_store()
    ollama_client = get_ollama_client()
    
    # Create orchestrator
    orchestrator = PydanticAgentOrchestrator(
        collection_id=collection_id,
        search_function=vector_store.search_documents,
        llm_function=ollama_client.generate_text
    )
    
    # Store session
    chat_sessions[session_id] = {
        "created_at": datetime.now(),
        "collection_id": collection_id,
        "orchestrator": orchestrator,
        "conversation_history": [],
        "current_state": {"phase": "initial"},
        "research_data": {},
        "outline_data": {},
        "user_preferences": {}
    }
    
    return session_id


async def format_stream_event(event_type: str, data: Any, session_id: str = None) -> str:
    """Format streaming event as SSE"""
    event = StreamEvent(
        event_type=event_type,
        data=data,
        session_id=session_id
    )
    return f"data: {event.model_dump_json()}\n\n"


async def stream_agent_response(
    orchestrator: PydanticAgentOrchestrator,
    workflow_type: str,
    session_id: str,
    **kwargs
) -> AsyncGenerator[str, None]:
    """Stream agent responses"""
    
    try:
        yield await format_stream_event("status", {
            "message": f"Starting {workflow_type} workflow...",
            "status": "processing"
        }, session_id)
        
        # Execute workflow based on type
        if workflow_type == "research":
            result = await orchestrator.start_research_workflow(**kwargs)
        elif workflow_type == "outline":
            result = await orchestrator.create_outline_workflow(**kwargs)
        elif workflow_type == "feedback":
            result = await orchestrator.handle_user_feedback_workflow(**kwargs)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        # Stream the response
        yield await format_stream_event("agent_response", {
            "workflow_type": workflow_type,
            "result": result.model_dump() if hasattr(result, 'model_dump') else result,
            "status": "completed"
        }, session_id)
        
        # Stream usage statistics
        usage_stats = orchestrator.get_usage_stats()
        yield await format_stream_event("usage_stats", usage_stats, session_id)
        
    except Exception as e:
        logger.error(f"Error in {workflow_type} workflow: {e}")
        yield await format_stream_event("error", {
            "message": f"Error in {workflow_type} workflow: {str(e)}",
            "workflow_type": workflow_type
        }, session_id)


@router.post("/start-session")
async def start_chat_session(request: ChatSessionRequest):
    """Start a new chat session"""
    
    # Generate session ID
    session_id = f"session_{datetime.now().timestamp()}_{request.collection_id}"
    
    try:
        # Create session
        await create_chat_session(session_id, request.collection_id)
        
        # Store user preferences
        if request.user_preferences:
            chat_sessions[session_id]["user_preferences"] = request.user_preferences
        
        # Add initial message to conversation
        chat_sessions[session_id]["conversation_history"].append({
            "role": "user",
            "content": request.initial_message.content,
            "timestamp": datetime.now(),
            "context": request.initial_message.context
        })
        
        return {
            "session_id": session_id,
            "status": "created",
            "message": "Chat session started successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.post("/research/{session_id}")
async def research_workflow(
    session_id: str,
    topic: str,
    subtopics: Optional[List[str]] = None
):
    """Start research workflow with streaming response"""
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    orchestrator = session["orchestrator"]
    
    # Add to conversation history
    session["conversation_history"].append({
        "role": "user",
        "content": f"Research topic: {topic}" + (f" with subtopics: {', '.join(subtopics)}" if subtopics else ""),
        "timestamp": datetime.now()
    })
    
    async def stream_research():
        async for event in stream_agent_response(
            orchestrator=orchestrator,
            workflow_type="research",
            session_id=session_id,
            topic=topic,
            subtopics=subtopics,
            user_preferences=session["user_preferences"]
        ):
            yield event
        
        # Update session state
        session["current_state"]["phase"] = "research_completed"
        yield await format_stream_event("phase_update", {
            "phase": "research_completed",
            "next_actions": ["create_outline", "refine_research"]
        }, session_id)
    
    return StreamingResponse(
        stream_research(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/outline/{session_id}")
async def outline_workflow(
    session_id: str,
    topic: str,
    use_existing_research: bool = True
):
    """Create outline workflow with streaming response"""
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    orchestrator = session["orchestrator"]
    
    # Get research data
    research_data = session.get("research_data", {}) if use_existing_research else {}
    
    # Add to conversation history
    session["conversation_history"].append({
        "role": "user",
        "content": f"Create outline for: {topic}",
        "timestamp": datetime.now()
    })
    
    async def stream_outline():
        async for event in stream_agent_response(
            orchestrator=orchestrator,
            workflow_type="outline",
            session_id=session_id,
            topic=topic,
            research_data=research_data,
            user_preferences=session["user_preferences"]
        ):
            yield event
        
        # Update session state
        session["current_state"]["phase"] = "outline_created"
        yield await format_stream_event("phase_update", {
            "phase": "outline_created",
            "next_actions": ["refine_outline", "generate_content", "export_outline"]
        }, session_id)
    
    return StreamingResponse(
        stream_outline(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/refine-outline/{session_id}")
async def refine_outline_workflow(request: OutlineRefinementRequest):
    """Refine outline based on user feedback"""
    
    if request.session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[request.session_id]
    orchestrator = session["orchestrator"]
    
    # Add to conversation history
    session["conversation_history"].append({
        "role": "user",
        "content": f"Refine outline: {request.user_feedback}",
        "timestamp": datetime.now()
    })
    
    async def stream_refinement():
        async for event in stream_agent_response(
            orchestrator=orchestrator,
            workflow_type="feedback",
            session_id=request.session_id,
            feedback=request.user_feedback,
            current_state={"outline": request.current_outline}
        ):
            yield event
        
        # Update session state
        session["current_state"]["phase"] = "outline_refined"
        yield await format_stream_event("phase_update", {
            "phase": "outline_refined",
            "next_actions": ["generate_content", "further_refinement"]
        }, request.session_id)
    
    return StreamingResponse(
        stream_refinement(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/message/{session_id}")
async def send_chat_message(session_id: str, message: ChatMessage):
    """Send a chat message and get agent response"""
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    orchestrator = session["orchestrator"]
    
    # Add user message to conversation
    session["conversation_history"].append({
        "role": "user",
        "content": message.content,
        "timestamp": datetime.now(),
        "context": message.context
    })
    
    async def stream_chat_response():
        # Analyze message to determine intent
        content_lower = message.content.lower()
        
        if any(word in content_lower for word in ["research", "find", "search"]):
            # Research intent
            yield await format_stream_event("intent_detected", {
                "intent": "research",
                "message": "I'll help you research this topic."
            }, session_id)
            
            # Extract topic from message
            topic = message.content  # Simplified - in production, use NLP
            
            async for event in stream_agent_response(
                orchestrator=orchestrator,
                workflow_type="research",
                session_id=session_id,
                topic=topic,
                user_preferences=session["user_preferences"]
            ):
                yield event
                
        elif any(word in content_lower for word in ["outline", "structure", "organize"]):
            # Outline intent
            yield await format_stream_event("intent_detected", {
                "intent": "outline",
                "message": "I'll create an outline for you."
            }, session_id)
            
            topic = message.content  # Simplified
            research_data = session.get("research_data", {})
            
            async for event in stream_agent_response(
                orchestrator=orchestrator,
                workflow_type="outline",
                session_id=session_id,
                topic=topic,
                research_data=research_data,
                user_preferences=session["user_preferences"]
            ):
                yield event
                
        else:
            # General feedback/refinement
            yield await format_stream_event("intent_detected", {
                "intent": "feedback",
                "message": "I'll help you refine your work."
            }, session_id)
            
            async for event in stream_agent_response(
                orchestrator=orchestrator,
                workflow_type="feedback",
                session_id=session_id,
                feedback=message.content,
                current_state=session["current_state"]
            ):
                yield event
        
        # Add agent response to conversation
        session["conversation_history"].append({
            "role": "assistant",
            "content": "Response completed",
            "timestamp": datetime.now()
        })
    
    return StreamingResponse(
        stream_chat_response(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    
    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "collection_id": session["collection_id"],
        "current_state": session["current_state"],
        "conversation_length": len(session["conversation_history"]),
        "user_preferences": session["user_preferences"]
    }


@router.get("/session/{session_id}/conversation")
async def get_conversation_history(session_id: str):
    """Get conversation history"""
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_id]
    
    return {
        "session_id": session_id,
        "conversation_history": session["conversation_history"],
        "total_messages": len(session["conversation_history"])
    }


@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End chat session"""
    
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get usage stats before deletion
    session = chat_sessions[session_id]
    orchestrator = session["orchestrator"]
    usage_stats = orchestrator.get_usage_stats()
    
    # Clean up session
    del chat_sessions[session_id]
    
    return {
        "session_id": session_id,
        "status": "ended",
        "final_usage_stats": usage_stats,
        "message": "Session ended successfully"
    }