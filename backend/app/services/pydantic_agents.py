"""
AI Agent orchestration using Pydantic AI for article generation workflow
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import Usage, UsageLimits
from pydantic_ai.messages import ModelMessage

logger = logging.getLogger(__name__)


class AgentResponse(BaseModel):
    """Standardized response format for all agents"""
    status: str = "success"
    data: Any = None
    message: str = ""
    agent_type: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class ResearchResult(BaseModel):
    """Research findings from knowledge base"""
    query: str
    relevant_chunks: List[Dict[str, Any]]
    total_found: int
    confidence_score: float = 0.0


class OutlineSection(BaseModel):
    """Article outline section"""
    title: str
    description: str
    key_points: List[str]
    estimated_words: int = 200


class ArticleOutline(BaseModel):
    """Complete article outline"""
    title: str
    introduction: str
    sections: List[OutlineSection]
    conclusion: str
    estimated_total_words: int
    writing_suggestions: List[str] = []


class OutlineRefinementSuggestion(BaseModel):
    """Suggestions for improving the outline"""
    section_id: int
    suggestion_type: str  # "add", "modify", "remove", "reorder"
    description: str
    reasoning: str


class ResearchRequest(BaseModel):
    """Request for research on specific topics"""
    main_topic: str
    specific_queries: List[str]
    depth_level: str = "comprehensive"  # "basic", "comprehensive", "detailed"


@dataclass
class AgentDependencies:
    """Shared dependencies across all agents"""
    collection_id: int
    search_function: Any
    llm_function: Any
    usage: Usage
    usage_limits: UsageLimits
    user_preferences: Dict[str, Any] = None


# Research Agent - Finds and analyzes relevant content
# Note: Agents are now created lazily to avoid initialization errors
def create_research_agent():
    """Create research agent with proper model configuration"""
    return Agent(
        'openai:gpt-4o-mini',  # Will be replaced with Ollama model
        deps_type=AgentDependencies,
        result_type=AgentResponse,
        system_prompt="""
        You are a Research Agent specialized in finding and analyzing relevant content from knowledge bases.
    
    Your role:
    1. Interpret research requests and break them into targeted search queries
    2. Analyze search results for relevance and quality
    3. Identify gaps in available information
    4. Suggest additional research directions
    5. Provide confidence scores for findings
    
    Always use the available search tools to find the most relevant and recent information.
    Focus on accuracy, relevance, and comprehensiveness.
    """
)


@research_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies], 
    query: str, 
    max_results: int = 10
) -> Dict[str, Any]:
    """Search the knowledge base for relevant content"""
    try:
        results = await ctx.deps.search_function(ctx.deps.collection_id, query)
        return {
            "query": query,
            "matches": results.get("matches", [])[:max_results],
            "total_found": results.get("total_matches", 0)
        }
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return {"query": query, "matches": [], "total_found": 0, "error": str(e)}


@research_agent.tool
async def analyze_content_quality(
    ctx: RunContext[AgentDependencies], 
    content_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze the quality and relevance of content chunks"""
    if not content_chunks:
        return {"quality_score": 0.0, "analysis": "No content to analyze"}
    
    # Simple quality analysis based on content length and preview quality
    total_chunks = len(content_chunks)
    quality_indicators = 0
    
    for chunk in content_chunks:
        preview = chunk.get("preview", "")
        if len(preview) > 100:  # Substantial content
            quality_indicators += 1
        if any(term in preview.lower() for term in ["research", "study", "analysis", "data"]):
            quality_indicators += 0.5
    
    quality_score = min(quality_indicators / total_chunks, 1.0) if total_chunks > 0 else 0.0
    
    return {
        "quality_score": quality_score,
        "total_chunks": total_chunks,
        "analysis": f"Quality score: {quality_score:.2f} based on {total_chunks} chunks"
    }


# Outline Agent - Creates and refines article outlines
outline_agent = Agent(
    'openai:gpt-4o-mini',
    deps_type=AgentDependencies,
    result_type=AgentResponse,
    system_prompt="""
    You are an Outline Agent specialized in creating comprehensive, well-structured article outlines.
    
    Your role:
    1. Create detailed article outlines based on research findings
    2. Ensure logical flow and comprehensive coverage
    3. Suggest improvements and refinements
    4. Adapt outlines based on user feedback
    5. Consider target audience and article goals
    
    Create outlines that are:
    - Logically structured with clear progression
    - Comprehensive yet focused
    - Engaging and reader-friendly
    - Appropriate for the target length and style
    """
)


@outline_agent.tool
async def create_outline_from_research(
    ctx: RunContext[AgentDependencies],
    topic: str,
    research_data: Dict[str, Any],
    article_type: str = "comprehensive",
    target_length: str = "medium"
) -> ArticleOutline:
    """Create an article outline based on research findings"""
    
    # Extract key themes from research
    key_themes = []
    if research_data.get("matches"):
        for match in research_data["matches"][:5]:  # Focus on top matches
            preview = match.get("preview", "")
            if preview:
                key_themes.append(preview[:100] + "..." if len(preview) > 100 else preview)
    
    # Define word targets based on length
    word_targets = {
        "short": {"total": 800, "section": 150},
        "medium": {"total": 1500, "section": 250},
        "long": {"total": 2500, "section": 400}
    }
    target = word_targets.get(target_length, word_targets["medium"])
    
    # Create sections based on research themes
    sections = []
    if key_themes:
        for i, theme in enumerate(key_themes[:6]):  # Max 6 sections
            sections.append(OutlineSection(
                title=f"Section {i+1}: {theme[:50]}...",
                description=f"Detailed analysis of {theme[:30]}...",
                key_points=[
                    f"Key point 1 for {theme[:20]}...",
                    f"Key point 2 for {theme[:20]}...",
                    f"Key point 3 for {theme[:20]}..."
                ],
                estimated_words=target["section"]
            ))
    
    return ArticleOutline(
        title=f"Comprehensive Guide to {topic}",
        introduction=f"An in-depth exploration of {topic} covering key aspects and insights.",
        sections=sections,
        conclusion=f"Summary and future implications of {topic}",
        estimated_total_words=target["total"],
        writing_suggestions=[
            f"Focus on {article_type} coverage",
            f"Target {target_length} length format",
            "Include relevant examples and case studies",
            "Maintain clear and engaging tone"
        ]
    )


@outline_agent.tool
async def suggest_outline_improvements(
    ctx: RunContext[AgentDependencies],
    current_outline: ArticleOutline,
    user_feedback: str
) -> List[OutlineRefinementSuggestion]:
    """Suggest improvements to the outline based on user feedback"""
    suggestions = []
    
    # Parse user feedback for specific requests
    feedback_lower = user_feedback.lower()
    
    if "more detail" in feedback_lower or "expand" in feedback_lower:
        suggestions.append(OutlineRefinementSuggestion(
            section_id=0,
            suggestion_type="modify",
            description="Add more detailed subsections",
            reasoning="User requested more detailed coverage"
        ))
    
    if "shorter" in feedback_lower or "concise" in feedback_lower:
        suggestions.append(OutlineRefinementSuggestion(
            section_id=0,
            suggestion_type="modify",
            description="Consolidate sections for brevity",
            reasoning="User requested more concise structure"
        ))
    
    if "add" in feedback_lower:
        suggestions.append(OutlineRefinementSuggestion(
            section_id=len(current_outline.sections),
            suggestion_type="add",
            description="Add new section based on user request",
            reasoning="User indicated missing content area"
        ))
    
    return suggestions


# Triage Agent - Orchestrates the overall workflow
triage_agent = Agent(
    'openai:gpt-4o-mini',
    deps_type=AgentDependencies,
    result_type=AgentResponse,
    system_prompt="""
    You are a Triage Agent responsible for orchestrating the article generation workflow.
    
    Your role:
    1. Coordinate between research and outline agents
    2. Determine the best approach based on user requests
    3. Handle user feedback and refine the process
    4. Ensure quality and completeness at each step
    5. Provide clear status updates and next steps
    
    Always consider:
    - User intent and preferences
    - Available research quality
    - Outline completeness and structure
    - Overall workflow efficiency
    """
)


@triage_agent.tool
async def coordinate_research_phase(
    ctx: RunContext[AgentDependencies],
    research_request: ResearchRequest
) -> AgentResponse:
    """Coordinate the research phase using the research agent"""
    
    # Run research agent for each query
    research_results = []
    
    for query in research_request.specific_queries:
        result = await research_agent.run(
            f"Research the topic: {query}",
            deps=ctx.deps,
            usage=ctx.deps.usage
        )
        research_results.append(result.data)
    
    return AgentResponse(
        status="success",
        data={
            "research_results": research_results,
            "main_topic": research_request.main_topic,
            "queries_processed": len(research_request.specific_queries)
        },
        message=f"Research completed for {len(research_request.specific_queries)} queries",
        agent_type="triage_research_coordinator"
    )


@triage_agent.tool
async def coordinate_outline_phase(
    ctx: RunContext[AgentDependencies],
    topic: str,
    research_data: Dict[str, Any],
    user_preferences: Optional[Dict[str, Any]] = None
) -> AgentResponse:
    """Coordinate the outline creation phase"""
    
    # Extract preferences
    prefs = user_preferences or {}
    article_type = prefs.get("article_type", "comprehensive")
    target_length = prefs.get("target_length", "medium")
    
    # Run outline agent
    result = await outline_agent.run(
        f"Create an outline for: {topic}",
        deps=ctx.deps,
        usage=ctx.deps.usage
    )
    
    return AgentResponse(
        status="success",
        data=result.data,
        message="Outline created successfully",
        agent_type="triage_outline_coordinator"
    )


@triage_agent.tool
async def handle_user_feedback(
    ctx: RunContext[AgentDependencies],
    feedback: str,
    current_state: Dict[str, Any]
) -> AgentResponse:
    """Handle user feedback and determine next actions"""
    
    feedback_lower = feedback.lower()
    next_actions = []
    
    # Determine what user wants to modify
    if "outline" in feedback_lower or "structure" in feedback_lower:
        next_actions.append("refine_outline")
    
    if "research" in feedback_lower or "more information" in feedback_lower:
        next_actions.append("additional_research")
    
    if "topic" in feedback_lower or "focus" in feedback_lower:
        next_actions.append("adjust_focus")
    
    if not next_actions:
        next_actions.append("clarify_request")
    
    return AgentResponse(
        status="success",
        data={
            "feedback_analysis": feedback,
            "recommended_actions": next_actions,
            "requires_user_input": "clarify_request" in next_actions
        },
        message=f"Feedback analyzed. Recommended actions: {', '.join(next_actions)}",
        agent_type="triage_feedback_handler"
    )


class PydanticAgentOrchestrator:
    """Main orchestrator for the Pydantic AI agent workflow"""
    
    def __init__(self, collection_id: int, search_function, llm_function):
        self.collection_id = collection_id
        self.search_function = search_function
        self.llm_function = llm_function
        self.usage = Usage()
        self.usage_limits = UsageLimits(request_limit=50, total_tokens_limit=100000)
        
    def _create_dependencies(self, user_preferences: Optional[Dict[str, Any]] = None) -> AgentDependencies:
        """Create agent dependencies"""
        return AgentDependencies(
            collection_id=self.collection_id,
            search_function=self.search_function,
            llm_function=self.llm_function,
            usage=self.usage,
            usage_limits=self.usage_limits,
            user_preferences=user_preferences or {}
        )
    
    async def start_research_workflow(
        self, 
        topic: str, 
        subtopics: Optional[List[str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Start the research workflow"""
        
        deps = self._create_dependencies(user_preferences)
        
        # Create research request
        queries = [topic]
        if subtopics:
            queries.extend(subtopics)
        
        research_request = ResearchRequest(
            main_topic=topic,
            specific_queries=queries,
            depth_level="comprehensive"
        )
        
        # Coordinate research
        result = await triage_agent.run(
            f"Start research for: {topic}",
            deps=deps,
            usage=self.usage
        )
        
        return result.data if result.data else AgentResponse(
            status="error",
            message="Research workflow failed",
            agent_type="orchestrator"
        )
    
    async def create_outline_workflow(
        self, 
        topic: str, 
        research_data: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Create outline workflow"""
        
        deps = self._create_dependencies(user_preferences)
        
        result = await triage_agent.run(
            f"Create outline for: {topic} based on research",
            deps=deps,
            usage=self.usage
        )
        
        return result.data if result.data else AgentResponse(
            status="error",
            message="Outline workflow failed",
            agent_type="orchestrator"
        )
    
    async def handle_user_feedback_workflow(
        self, 
        feedback: str, 
        current_state: Dict[str, Any]
    ) -> AgentResponse:
        """Handle user feedback workflow"""
        
        deps = self._create_dependencies()
        
        result = await triage_agent.run(
            f"Handle user feedback: {feedback}",
            deps=deps,
            usage=self.usage
        )
        
        return result.data if result.data else AgentResponse(
            status="error",
            message="Feedback handling failed",
            agent_type="orchestrator"
        )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_requests": self.usage.requests,
            "total_tokens": self.usage.total_tokens,
            "request_tokens": self.usage.request_tokens,
            "response_tokens": self.usage.response_tokens
        }