"""
Enhanced AI Agent orchestration using Pydantic AI for iterative article generation
with section-by-section feedback loops and comprehensive refinement system
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

logger = logging.getLogger(__name__)


class GenerationPhase(str, Enum):
    """Different phases of article generation"""
    RESEARCH = "research"
    OUTLINE = "outline"
    SECTION_GENERATION = "section_generation"
    SECTION_REFINEMENT = "section_refinement"
    FINAL_REVIEW = "final_review"
    COMPLETED = "completed"


class FeedbackType(str, Enum):
    """Types of feedback that can be provided"""
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    ADD_CONTENT = "add_content"
    REMOVE_CONTENT = "remove_content"
    RESTRUCTURE = "restructure"
    STYLE_ADJUSTMENT = "style_adjustment"


class AgentResponse(BaseModel):
    """Standardized response format for all agents"""
    status: str = "success"
    data: Any = None
    message: str = ""
    agent_type: str = ""
    phase: GenerationPhase
    timestamp: datetime = Field(default_factory=datetime.now)
    requires_feedback: bool = False
    suggestions: List[str] = []


class SectionContent(BaseModel):
    """Individual section content with metadata"""
    section_id: str
    title: str
    content: str
    word_count: int
    status: Literal["draft", "approved", "needs_revision"] = "draft"
    feedback_history: List[Dict[str, Any]] = []
    sources_used: List[str] = []
    confidence_score: float = 0.0


class ArticleOutline(BaseModel):
    """Enhanced article outline with feedback tracking"""
    title: str
    introduction: str
    sections: List[Dict[str, Any]]  # Will contain section metadata
    conclusion: str
    estimated_total_words: int
    writing_style: str = "professional"
    target_audience: str = "general"
    feedback_history: List[Dict[str, Any]] = []
    approval_status: Literal["draft", "approved", "needs_revision"] = "draft"


class SectionFeedback(BaseModel):
    """Feedback for individual sections"""
    section_id: str
    feedback_type: FeedbackType
    feedback_text: str
    specific_changes: Optional[str] = None
    priority: Literal["low", "medium", "high"] = "medium"
    timestamp: datetime = Field(default_factory=datetime.now)


class ArticleFeedback(BaseModel):
    """Overall article feedback"""
    feedback_type: FeedbackType
    feedback_text: str
    section_feedback: List[SectionFeedback] = []
    overall_suggestions: List[str] = []
    priority: Literal["low", "medium", "high"] = "medium"


class GenerationState(BaseModel):
    """Current state of article generation process"""
    article_id: Optional[int] = None
    collection_id: int
    topic: str
    current_phase: GenerationPhase
    outline: Optional[ArticleOutline] = None
    sections: Dict[str, SectionContent] = {}
    current_section_id: Optional[str] = None
    feedback_queue: List[Union[SectionFeedback, ArticleFeedback]] = []
    generation_history: List[Dict[str, Any]] = []
    user_preferences: Dict[str, Any] = {}


@dataclass
class AgentDependencies:
    """Enhanced dependencies for all agents"""
    collection_id: int
    search_function: Any
    llm_function: Any
    web_search_function: Optional[Any] = None
    generation_state: Optional[GenerationState] = None
    user_preferences: Dict[str, Any] = None


def create_research_agent(model_name: str = 'llama3.2:3b'):
    """Enhanced research agent with web search fallback"""
    return Agent(
        f'ollama:{model_name}',
        deps_type=AgentDependencies,
        result_type=AgentResponse,
        system_prompt="""
        You are an Enhanced Research Agent specialized in comprehensive content research.
        
        Your capabilities:
        1. Search local knowledge base for relevant content
        2. Use web search as fallback when local content is insufficient
        3. Analyze and synthesize information from multiple sources
        4. Provide confidence scores and source attribution
        5. Identify knowledge gaps and suggest additional research
        
        Always prioritize accuracy, relevance, and comprehensive coverage.
        When using web search, focus on recent and authoritative sources.
        """
    )


def create_outline_agent(model_name: str = 'llama3.2:3b'):
    """Agent for creating and refining article outlines"""
    return Agent(
        f'ollama:{model_name}',
        deps_type=AgentDependencies,
        result_type=AgentResponse,
        system_prompt="""
        You are an Outline Architect Agent specialized in creating structured, comprehensive article outlines.
        
        Your responsibilities:
        1. Create well-structured outlines based on research findings
        2. Ensure logical flow and comprehensive coverage
        3. Adapt structure to article type and target length
        4. Incorporate user feedback and refinement requests
        5. Provide section-level guidance for content generation
        
        Focus on creating outlines that facilitate section-by-section generation and review.
        Each section should be self-contained but contribute to the overall narrative.
        """
    )


def create_section_writer_agent(model_name: str = 'llama3.2:3b'):
    """Agent for generating individual article sections"""
    return Agent(
        f'ollama:{model_name}',
        deps_type=AgentDependencies,
        result_type=AgentResponse,
        system_prompt="""
        You are a Section Writer Agent specialized in creating high-quality article sections.
        
        Your role:
        1. Generate comprehensive content for individual sections
        2. Maintain consistency with the overall article outline and style
        3. Incorporate relevant research findings and sources
        4. Adapt writing style to target audience and article type
        5. Ensure each section flows well and meets word count targets
        
        Each section should be complete, well-researched, and ready for review.
        Always cite sources appropriately and maintain factual accuracy.
        """
    )


def create_refinement_agent(model_name: str = 'llama3.2:3b'):
    """Agent for processing feedback and refining content"""
    return Agent(
        f'ollama:{model_name}',
        deps_type=AgentDependencies,
        result_type=AgentResponse,
        system_prompt="""
        You are a Refinement Specialist Agent focused on improving content based on user feedback.
        
        Your expertise:
        1. Analyze user feedback and identify specific improvement areas
        2. Refine content while maintaining original intent and quality
        3. Implement structural changes, style adjustments, and content additions
        4. Ensure consistency across refined sections
        5. Provide clear explanations of changes made
        
        Always preserve the core message while implementing requested improvements.
        Be responsive to user preferences and maintain high content quality.
        """
    )


def create_review_agent(model_name: str = 'llama3.2:3b'):
    """Agent for final review and quality assurance"""
    return Agent(
        f'ollama:{model_name}',
        deps_type=AgentDependencies,
        result_type=AgentResponse,
        system_prompt="""
        You are a Quality Assurance Agent responsible for final article review.
        
        Your responsibilities:
        1. Review complete articles for coherence, flow, and quality
        2. Check for factual consistency and proper source attribution
        3. Ensure adherence to style guidelines and target specifications
        4. Identify areas for final improvements
        5. Provide comprehensive quality assessment
        
        Focus on overall article quality, readability, and meeting user requirements.
        Provide actionable feedback for any remaining improvements.
        """
    )


# Agent tool functions
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies], 
    query: str, 
    max_results: int = 10
) -> Dict[str, Any]:
    """Search the knowledge base for relevant content"""
    try:
        deps = ctx.deps
        results = await deps.search_function(deps.collection_id, query, max_results)
        
        return {
            "query": query,
            "results": results.get("matches", []),
            "total_found": results.get("total_matches", 0),
            "source_type": "local_knowledge_base"
        }
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        # Try web search as fallback
        if ctx.deps.web_search_function:
            try:
                web_results = await ctx.deps.web_search_function(query, max_results=5)
                return {
                    "query": query,
                    "results": web_results,
                    "total_found": len(web_results),
                    "source_type": "web_search"
                }
            except Exception as web_error:
                logger.error(f"Web search fallback failed: {web_error}")
        
        return {"query": query, "results": [], "total_found": 0, "error": str(e)}


async def generate_section_content(
    ctx: RunContext[AgentDependencies],
    section_title: str,
    section_context: str,
    research_data: Dict[str, Any],
    writing_style: str = "professional"
) -> Dict[str, Any]:
    """Generate content for a specific section"""
    try:
        deps = ctx.deps
        
        # Use the LLM function to generate section content
        prompt = f"""
        Generate a comprehensive section for an article with the following specifications:
        
        Section Title: {section_title}
        Context: {section_context}
        Writing Style: {writing_style}
        
        Research Data Available:
        {json.dumps(research_data, indent=2)}
        
        Requirements:
        1. Create engaging, well-structured content
        2. Incorporate relevant research findings naturally
        3. Maintain the specified writing style
        4. Include specific examples and details where appropriate
        5. Ensure the section flows well and is approximately 300-500 words
        6. Cite sources appropriately
        
        Generate only the section content without the heading.
        """
        
        content = await deps.llm_function(prompt, max_tokens=800)
        
        return {
            "title": section_title,
            "content": content.strip(),
            "word_count": len(content.split()),
            "sources_used": [item.get("source", "") for item in research_data.get("results", [])[:3]],
            "confidence_score": 0.8  # Could be calculated based on research quality
        }
        
    except Exception as e:
        logger.error(f"Section generation failed: {e}")
        return {"error": str(e)}


async def refine_content_with_feedback(
    ctx: RunContext[AgentDependencies],
    original_content: str,
    feedback: str,
    feedback_type: str
) -> Dict[str, Any]:
    """Refine content based on user feedback"""
    try:
        deps = ctx.deps
        
        prompt = f"""
        Refine the following content based on user feedback:
        
        Original Content:
        {original_content}
        
        User Feedback:
        {feedback}
        
        Feedback Type: {feedback_type}
        
        Instructions:
        1. Carefully analyze the feedback and identify specific improvement areas
        2. Implement the requested changes while maintaining content quality
        3. Preserve the core message and factual accuracy
        4. Ensure the refined content flows well and is coherent
        5. If the feedback requests additions, integrate them naturally
        6. If the feedback requests removals, ensure smooth transitions
        
        Provide the refined content:
        """
        
        refined_content = await deps.llm_function(prompt, max_tokens=1000, is_refinement=True)
        
        return {
            "refined_content": refined_content.strip(),
            "changes_made": "Content refined based on user feedback",
            "word_count": len(refined_content.split())
        }
        
    except Exception as e:
        logger.error(f"Content refinement failed: {e}")
        return {"error": str(e)}


class EnhancedAgentOrchestrator:
    """Enhanced orchestrator for managing the complete article generation workflow"""
    
    def __init__(self, collection_id: int, search_function, llm_function, web_search_function=None, model_name: str = 'llama3.2:3b'):
        self.collection_id = collection_id
        self.search_function = search_function
        self.llm_function = llm_function
        self.web_search_function = web_search_function
        self.model_name = model_name
        
        # Initialize agents
        self.research_agent = create_research_agent(model_name)
        self.outline_agent = create_outline_agent(model_name)
        self.section_writer_agent = create_section_writer_agent(model_name)
        self.refinement_agent = create_refinement_agent(model_name)
        self.review_agent = create_review_agent(model_name)
        
        # Register tools with agents
        self._register_agent_tools()
        
        # Active generation states (session management)
        self.active_generations: Dict[str, GenerationState] = {}
    
    def _register_agent_tools(self):
        """Register tools with all agents"""
        # Research agent tools
        self.research_agent.tool(search_knowledge_base)
        
        # Section writer agent tools  
        self.section_writer_agent.tool(generate_section_content)
        
        # Refinement agent tools
        self.refinement_agent.tool(refine_content_with_feedback)
    
    def _create_dependencies(self, generation_state: GenerationState) -> AgentDependencies:
        """Create agent dependencies for the current generation state"""
        return AgentDependencies(
            collection_id=self.collection_id,
            search_function=self.search_function,
            llm_function=self.llm_function,
            web_search_function=self.web_search_function,
            generation_state=generation_state,
            user_preferences=generation_state.user_preferences
        )
    
    async def start_article_generation(
        self, 
        topic: str, 
        article_type: str = "comprehensive",
        target_length: str = "medium",
        writing_style: str = "professional",
        user_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Start a new article generation session"""
        
        session_id = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        generation_state = GenerationState(
            collection_id=self.collection_id,
            topic=topic,
            current_phase=GenerationPhase.RESEARCH,
            user_preferences=user_preferences or {}
        )
        
        self.active_generations[session_id] = generation_state
        
        logger.info(f"🚀 Started article generation session: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "started",
            "current_phase": GenerationPhase.RESEARCH,
            "message": f"Article generation started for topic: {topic}"
        }
    
    async def process_research_phase(self, session_id: str) -> Dict[str, Any]:
        """Process the research phase"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        deps = self._create_dependencies(state)
        
        # Run research agent
        research_result = await self.research_agent.run(
            f"Research comprehensive information about: {state.topic}",
            deps=deps
        )
        
        # Update state
        state.current_phase = GenerationPhase.OUTLINE
        state.generation_history.append({
            "phase": GenerationPhase.RESEARCH,
            "result": research_result.data,
            "timestamp": datetime.now()
        })
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.RESEARCH,
            "status": "completed",
            "data": research_result.data,
            "next_phase": GenerationPhase.OUTLINE
        }
    
    async def generate_outline(self, session_id: str, research_feedback: str = "") -> Dict[str, Any]:
        """Generate article outline based on research"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        deps = self._create_dependencies(state)
        
        # Get research data from history
        research_data = None
        for entry in state.generation_history:
            if entry["phase"] == GenerationPhase.RESEARCH:
                research_data = entry["result"]
                break
        
        outline_prompt = f"""
        Create a comprehensive outline for an article about: {state.topic}
        
        Research Data:
        {json.dumps(research_data, indent=2) if research_data else "No research data available"}
        
        {f"User Research Feedback: {research_feedback}" if research_feedback else ""}
        
        Requirements:
        - Create a structured outline with clear sections
        - Each section should be detailed enough for independent generation
        - Ensure logical flow and comprehensive coverage
        - Provide estimated word counts for each section
        """
        
        outline_result = await self.outline_agent.run(outline_prompt, deps=deps)
        
        # Update state
        state.current_phase = GenerationPhase.SECTION_GENERATION
        state.outline = ArticleOutline(
            title=f"Article: {state.topic}",
            introduction="Introduction section",
            sections=[],  # Will be populated from outline_result
            conclusion="Conclusion section",
            estimated_total_words=1000  # Will be calculated
        )
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.OUTLINE,
            "status": "completed",
            "outline": outline_result.data,
            "requires_feedback": True,
            "next_phase": GenerationPhase.SECTION_GENERATION
        }
    
    async def generate_section(
        self, 
        session_id: str, 
        section_id: str,
        section_feedback: str = ""
    ) -> Dict[str, Any]:
        """Generate content for a specific section"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        deps = self._create_dependencies(state)
        
        # Get section details from outline
        if not state.outline or not state.outline.sections:
            raise ValueError("No outline available for section generation")
        
        # Find the specific section
        section_data = None
        for section in state.outline.sections:
            if section.get("id") == section_id:
                section_data = section
                break
        
        if not section_data:
            raise ValueError(f"Section {section_id} not found in outline")
        
        # Generate section content
        section_result = await self.section_writer_agent.run(
            f"Generate content for section: {section_data.get('title', 'Untitled Section')}",
            deps=deps
        )
        
        # Create section content object
        section_content = SectionContent(
            section_id=section_id,
            title=section_data.get('title', 'Untitled Section'),
            content=section_result.data.get('content', ''),
            word_count=section_result.data.get('word_count', 0),
            sources_used=section_result.data.get('sources_used', []),
            confidence_score=section_result.data.get('confidence_score', 0.0)
        )
        
        # Store section
        state.sections[section_id] = section_content
        state.current_section_id = section_id
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.SECTION_GENERATION,
            "section_id": section_id,
            "status": "completed",
            "section_content": section_content.dict(),
            "requires_feedback": True,
            "next_action": "provide_section_feedback_or_continue"
        }
    
    async def process_section_feedback(
        self,
        session_id: str,
        section_id: str,
        feedback: SectionFeedback
    ) -> Dict[str, Any]:
        """Process feedback for a specific section"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        if section_id not in state.sections:
            raise ValueError(f"Section {section_id} not found")
        
        section = state.sections[section_id]
        
        if feedback.feedback_type == FeedbackType.APPROVE:
            section.status = "approved"
            section.feedback_history.append(feedback.dict())
            
            return {
                "session_id": session_id,
                "section_id": section_id,
                "status": "approved",
                "message": "Section approved, ready for next section or final review"
            }
        
        else:
            # Process refinement feedback
            deps = self._create_dependencies(state)
            
            refinement_result = await self.refinement_agent.run(
                f"Refine section based on feedback: {feedback.feedback_text}",
                deps=deps
            )
            
            # Update section with refined content
            section.content = refinement_result.data.get('refined_content', section.content)
            section.word_count = refinement_result.data.get('word_count', section.word_count)
            section.status = "needs_revision"
            section.feedback_history.append(feedback.dict())
            
            return {
                "session_id": session_id,
                "section_id": section_id,
                "status": "refined",
                "refined_content": section.content,
                "changes_made": refinement_result.data.get('changes_made', ''),
                "requires_feedback": True
            }
    
    async def finalize_article(self, session_id: str) -> Dict[str, Any]:
        """Finalize the complete article"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        # Check if all sections are approved
        unapproved_sections = [
            section_id for section_id, section in state.sections.items()
            if section.status != "approved"
        ]
        
        if unapproved_sections:
            return {
                "session_id": session_id,
                "status": "pending_approval",
                "message": f"Sections still need approval: {', '.join(unapproved_sections)}",
                "unapproved_sections": unapproved_sections
            }
        
        # Compile final article
        final_content = []
        
        # Add introduction
        if state.outline and state.outline.introduction:
            final_content.append(f"# {state.outline.title}\n\n{state.outline.introduction}\n\n")
        
        # Add all approved sections
        for section_id in sorted(state.sections.keys()):
            section = state.sections[section_id]
            final_content.append(f"## {section.title}\n\n{section.content}\n\n")
        
        # Add conclusion
        if state.outline and state.outline.conclusion:
            final_content.append(f"## Conclusion\n\n{state.outline.conclusion}\n\n")
        
        final_article = "".join(final_content)
        total_words = sum(section.word_count for section in state.sections.values())
        
        # Update state
        state.current_phase = GenerationPhase.FINAL_REVIEW
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.FINAL_REVIEW,
            "status": "completed",
            "final_article": final_article,
            "total_words": total_words,
            "sections_count": len(state.sections),
            "requires_final_feedback": True
        }
    
    async def process_final_feedback(
        self,
        session_id: str,
        feedback: ArticleFeedback
    ) -> Dict[str, Any]:
        """Process final article feedback"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        deps = self._create_dependencies(state)
        
        if feedback.feedback_type == FeedbackType.APPROVE:
            state.current_phase = GenerationPhase.COMPLETED
            
            return {
                "session_id": session_id,
                "status": "completed",
                "message": "Article generation completed successfully!"
            }
        
        else:
            # Process section-specific feedback
            refinement_results = []
            
            for section_feedback in feedback.section_feedback:
                section_result = await self.process_section_feedback(
                    session_id, 
                    section_feedback.section_id, 
                    section_feedback
                )
                refinement_results.append(section_result)
            
            return {
                "session_id": session_id,
                "status": "refined",
                "message": "Article refined based on feedback",
                "refinement_results": refinement_results,
                "requires_final_review": True
            }
    
    def get_generation_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of article generation"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        return {
            "session_id": session_id,
            "current_phase": state.current_phase,
            "topic": state.topic,
            "sections_completed": len([s for s in state.sections.values() if s.status == "approved"]),
            "total_sections": len(state.sections),
            "feedback_queue_length": len(state.feedback_queue),
            "generation_history": state.generation_history
        }
    
    def cleanup_session(self, session_id: str):
        """Clean up completed session"""
        if session_id in self.active_generations:
            del self.active_generations[session_id]
            logger.info(f"🧹 Cleaned up session: {session_id}")