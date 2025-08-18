"""
Simplified Enhanced Agent System that integrates with existing Ollama infrastructure
Uses Pydantic AI concepts but works with our current setup
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

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
    sections: List[Dict[str, Any]]
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
    current_section_index: int = 0
    section_order: List[str] = []
    section_refinement_mode: bool = False
    final_article: Optional[str] = None
    final_refinement_mode: bool = False
    feedback_queue: List[Union[SectionFeedback, ArticleFeedback]] = []
    generation_history: List[Dict[str, Any]] = []
    user_preferences: Dict[str, Any] = {}


class ResearchAgent:
    """Agent for research tasks"""
    
    def __init__(self, search_function, llm_function, web_search_function=None):
        self.search_function = search_function
        self.llm_function = llm_function
        self.web_search_function = web_search_function
    
    async def research_topic(self, topic: str, collection_id: int) -> Dict[str, Any]:
        """Research a topic using available sources"""
        logger.info(f"🔍 Research Agent starting research for: {topic}")
        
        research_results = {
            "topic": topic,
            "local_results": [],
            "web_results": [],
            "total_sources": 0,
            "source_type": "local_knowledge_base",
            "confidence_score": 0.0
        }
        
        try:
            # Try local search first
            local_results = await self.search_function(collection_id, topic, limit=10)
            if local_results and local_results.get("matches"):
                research_results["local_results"] = local_results["matches"]
                research_results["total_sources"] = len(local_results["matches"])
                research_results["confidence_score"] = 0.8
                logger.info(f"📚 Found {len(local_results['matches'])} local sources")
            
            # If no local results, try web search
            if research_results["total_sources"] == 0 and self.web_search_function:
                try:
                    web_results = await self.web_search_function(topic, max_results=5)
                    if web_results:
                        research_results["web_results"] = web_results
                        research_results["total_sources"] = len(web_results)
                        research_results["source_type"] = "web_search"
                        research_results["confidence_score"] = 0.6
                        logger.info(f"🌐 Found {len(web_results)} web sources")
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
            
            return research_results
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return research_results


class OutlineAgent:
    """Agent for creating article outlines"""
    
    def __init__(self, llm_function):
        self.llm_function = llm_function
    
    async def create_outline(self, topic: str, research_data: Dict[str, Any], article_type: str = "comprehensive") -> Dict[str, Any]:
        """Create an article outline based on research"""
        logger.info(f"📝 Outline Agent creating outline for: {topic}")
        
        # Prepare research context
        research_context = ""
        if research_data.get("local_results"):
            research_context += "Local Knowledge Base Results:\n"
            for result in research_data["local_results"][:3]:
                research_context += f"- {result.get('text', '')[:200]}...\n"
        
        if research_data.get("web_results"):
            research_context += "\nWeb Search Results:\n"
            for result in research_data["web_results"][:3]:
                research_context += f"- {result.get('title', '')}: {result.get('snippet', '')[:150]}...\n"
        
        prompt = f"""
        Create a comprehensive outline for a {article_type} article about: {topic}
        
        Research Context:
        {research_context}
        
        Requirements:
        1. Create a clear, structured outline with 4-6 main sections
        2. Each section should have a descriptive title and 2-3 key points
        3. Ensure logical flow from introduction to conclusion
        4. Make each section substantial enough for detailed content generation
        5. Include estimated word count for each section (aim for 300-500 words per section)
        
        Format the outline as a structured text with clear section headers and bullet points.
        """
        
        try:
            outline_text = await self.llm_function(prompt, max_tokens=800)
            
            # Parse the outline into structured format
            sections = self._parse_outline_text(outline_text)
            
            outline = ArticleOutline(
                title=f"Article: {topic}",
                sections=sections,
                estimated_total_words=len(sections) * 400,  # Estimate 400 words per section
                writing_style="professional"
            )
            
            return {
                "outline": outline.dict(),
                "outline_text": outline_text,
                "sections_count": len(sections)
            }
            
        except Exception as e:
            logger.error(f"Outline creation failed: {e}")
            raise
    
    def _parse_outline_text(self, outline_text: str) -> List[Dict[str, Any]]:
        """Parse outline text into structured sections"""
        sections = []
        current_section = None
        
        lines = outline_text.split('\n')
        section_counter = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers (lines that start with numbers, ##, or are in caps)
            if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.')) or 
                line.startswith('##') or 
                (line.isupper() and len(line) > 5)):
                
                if current_section:
                    sections.append(current_section)
                
                section_counter += 1
                current_section = {
                    "id": f"section_{section_counter}",
                    "title": line.lstrip('0123456789.# ').title(),
                    "description": "",
                    "key_points": [],
                    "estimated_words": 400
                }
            
            elif line.startswith(('-', '•', '*')) and current_section:
                # Key points
                current_section["key_points"].append(line.lstrip('-•* '))
            
            elif current_section and not current_section["description"]:
                # Description line
                current_section["description"] = line
        
        # Add the last section
        if current_section:
            sections.append(current_section)
        
        # Ensure we have at least some sections
        if not sections:
            sections = [
                {
                    "id": "section_1",
                    "title": "Introduction",
                    "description": f"Introduction to {outline_text[:100]}",
                    "key_points": ["Background", "Context", "Overview"],
                    "estimated_words": 300
                },
                {
                    "id": "section_2", 
                    "title": "Main Content",
                    "description": "Main discussion and analysis",
                    "key_points": ["Key concepts", "Analysis", "Examples"],
                    "estimated_words": 500
                },
                {
                    "id": "section_3",
                    "title": "Conclusion",
                    "description": "Summary and conclusions",
                    "key_points": ["Summary", "Implications", "Future outlook"],
                    "estimated_words": 300
                }
            ]
        
        return sections


class SectionWriterAgent:
    """Agent for writing individual sections"""
    
    def __init__(self, llm_function):
        self.llm_function = llm_function
    
    async def write_section(self, section_data: Dict[str, Any], topic: str, research_data: Dict[str, Any]) -> SectionContent:
        """Write content for a specific section"""
        section_title = section_data.get("title", "Untitled Section")
        logger.info(f"✍️ Section Writer Agent writing: {section_title}")
        
        # Prepare context
        context = f"Article Topic: {topic}\n"
        context += f"Section: {section_title}\n"
        context += f"Description: {section_data.get('description', '')}\n"
        context += f"Key Points: {', '.join(section_data.get('key_points', []))}\n"
        
        # Add relevant research
        research_context = ""
        if research_data.get("local_results"):
            research_context += "Relevant Sources:\n"
            for result in research_data["local_results"][:2]:
                research_context += f"- {result.get('text', '')[:300]}...\n"
        
        prompt = f"""
        Write a comprehensive section for an article with the following context:
        
        {context}
        
        Research Information:
        {research_context}
        
        Requirements:
        1. Write 300-500 words of high-quality content
        2. Focus specifically on the section topic and key points
        3. Use clear, engaging language appropriate for a general audience
        4. Include specific details and examples where relevant
        5. Ensure the content flows well and is informative
        6. Do not include the section title in the output
        
        Write only the section content:
        """
        
        try:
            content = await self.llm_function(prompt, max_tokens=700)
            
            section_content = SectionContent(
                section_id=section_data.get("id", "unknown"),
                title=section_title,
                content=content.strip(),
                word_count=len(content.split()),
                sources_used=[result.get("source", "") for result in research_data.get("local_results", [])[:2]],
                confidence_score=0.8
            )
            
            return section_content
            
        except Exception as e:
            logger.error(f"Section writing failed: {e}")
            raise


class RefinementAgent:
    """Agent for refining content based on feedback"""
    
    def __init__(self, llm_function):
        self.llm_function = llm_function
    
    async def refine_content(self, original_content: str, feedback: str, feedback_type: str) -> Dict[str, Any]:
        """Refine content based on user feedback"""
        logger.info(f"🔧 Refinement Agent processing {feedback_type} feedback")
        
        prompt = f"""
        Refine the following content based on user feedback:
        
        Original Content:
        {original_content}
        
        User Feedback: {feedback}
        Feedback Type: {feedback_type}
        
        Instructions:
        1. Carefully analyze the feedback and implement the requested changes
        2. Maintain the core message and factual accuracy
        3. Ensure the refined content flows well and is coherent
        4. If adding content, integrate it naturally
        5. If removing content, ensure smooth transitions
        6. Preserve the professional tone and style
        
        Provide the refined content:
        """
        
        try:
            refined_content = await self.llm_function(prompt, max_tokens=800, is_refinement=True)
            
            return {
                "refined_content": refined_content.strip(),
                "changes_made": f"Content refined based on {feedback_type} feedback",
                "word_count": len(refined_content.split())
            }
            
        except Exception as e:
            logger.error(f"Content refinement failed: {e}")
            raise


class SimplifiedAgentOrchestrator:
    """Simplified orchestrator that works with existing infrastructure"""
    
    def __init__(self, collection_id: int, search_function, llm_function, web_search_function=None):
        self.collection_id = collection_id
        self.search_function = search_function
        self.llm_function = llm_function
        self.web_search_function = web_search_function
        
        # Initialize agents
        self.research_agent = ResearchAgent(search_function, llm_function, web_search_function)
        self.outline_agent = OutlineAgent(llm_function)
        self.section_writer_agent = SectionWriterAgent(llm_function)
        self.refinement_agent = RefinementAgent(llm_function)
        
        # Active generation states
        self.active_generations: Dict[str, GenerationState] = {}
        
        logger.info(f"🤖 Simplified Agent Orchestrator initialized for collection {collection_id}")
    
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
        
        # Run research
        research_result = await self.research_agent.research_topic(state.topic, state.collection_id)
        
        # Update state
        state.current_phase = GenerationPhase.OUTLINE
        state.generation_history.append({
            "phase": GenerationPhase.RESEARCH,
            "result": research_result,
            "timestamp": datetime.now()
        })
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.RESEARCH,
            "status": "completed",
            "data": research_result,
            "next_phase": GenerationPhase.OUTLINE
        }
    
    async def generate_outline(self, session_id: str, research_feedback: str = "") -> Dict[str, Any]:
        """Generate article outline based on research"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        # Get research data from history
        research_data = None
        for entry in state.generation_history:
            if entry["phase"] == GenerationPhase.RESEARCH:
                research_data = entry["result"]
                break
        
        if not research_data:
            raise ValueError("No research data available for outline generation")
        
        # Generate outline
        outline_result = await self.outline_agent.create_outline(
            state.topic, 
            research_data, 
            state.user_preferences.get("article_type", "comprehensive")
        )
        
        # Update state
        state.current_phase = GenerationPhase.SECTION_GENERATION
        state.outline = ArticleOutline(**outline_result["outline"])
        
        # Set up section order for step-by-step generation
        state.section_order = [section.get("id") for section in state.outline.sections]
        state.current_section_index = 0
        if state.section_order:
            state.current_section_id = state.section_order[0]
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.OUTLINE,
            "status": "completed",
            "outline": outline_result,
            "section_order": state.section_order,
            "total_sections": len(state.section_order),
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
        
        # Get research data
        research_data = {}
        for entry in state.generation_history:
            if entry["phase"] == GenerationPhase.RESEARCH:
                research_data = entry["result"]
                break
        
        # Generate section content
        section_content = await self.section_writer_agent.write_section(
            section_data, 
            state.topic, 
            research_data
        )
        
        # Store section
        state.sections[section_id] = section_content
        state.current_section_id = section_id
        state.section_refinement_mode = True
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.SECTION_GENERATION,
            "section_id": section_id,
            "section_index": state.current_section_index + 1,
            "total_sections": len(state.section_order),
            "status": "completed",
            "section_content": section_content.dict(),
            "in_refinement_mode": True,
            "requires_feedback": True,
            "next_action": "refine_section_or_move_on"
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
            refinement_result = await self.refinement_agent.refine_content(
                section.content,
                feedback.feedback_text,
                feedback.feedback_type.value
            )
            
            # Update section with refined content
            section.content = refinement_result.get('refined_content', section.content)
            section.word_count = refinement_result.get('word_count', section.word_count)
            section.status = "needs_revision"
            section.feedback_history.append(feedback.dict())
            
            return {
                "session_id": session_id,
                "section_id": section_id,
                "status": "refined",
                "refined_content": section.content,
                "changes_made": refinement_result.get('changes_made', ''),
                "in_refinement_mode": True,
                "requires_feedback": True
            }
    
    async def move_to_next_section(self, session_id: str) -> Dict[str, Any]:
        """Move to the next section in the workflow"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        # Mark current section as completed
        if state.current_section_id and state.current_section_id in state.sections:
            state.sections[state.current_section_id].status = "approved"
        
        # Move to next section
        state.current_section_index += 1
        state.section_refinement_mode = False
        
        if state.current_section_index < len(state.section_order):
            # Still have sections to generate
            next_section_id = state.section_order[state.current_section_index]
            state.current_section_id = next_section_id
            
            return {
                "session_id": session_id,
                "status": "moved_to_next",
                "next_section_id": next_section_id,
                "section_index": state.current_section_index + 1,
                "total_sections": len(state.section_order),
                "message": f"Ready to generate next section",
                "action_needed": "generate_next_section"
            }
        else:
            # All sections complete, move to final article review
            final_article = await self._compile_final_article(state)
            state.final_article = final_article
            state.current_phase = GenerationPhase.FINAL_REVIEW
            state.final_refinement_mode = True
            
            return {
                "session_id": session_id,
                "status": "all_sections_complete",
                "final_article": final_article,
                "total_words": sum(section.word_count for section in state.sections.values()),
                "phase": GenerationPhase.FINAL_REVIEW,
                "message": "All sections complete. Review the final article.",
                "action_needed": "final_review"
            }
    
    async def _compile_final_article(self, state: GenerationState) -> str:
        """Compile all sections into final article"""
        final_content = []
        
        # Add title
        if state.outline and state.outline.title:
            final_content.append(f"# {state.outline.title}\n\n")
        
        # Add all sections in order
        for section_id in state.section_order:
            if section_id in state.sections:
                section = state.sections[section_id]
                final_content.append(f"## {section.title}\n\n{section.content}\n\n")
        
        return "".join(final_content)
    
    async def refine_final_article(self, session_id: str, feedback: str) -> Dict[str, Any]:
        """Refine the complete final article based on feedback"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        if not state.final_article:
            raise ValueError("No final article available for refinement")
        
        # Use refinement agent to improve the complete article
        refinement_result = await self.refinement_agent.refine_content(
            state.final_article,
            feedback,
            "overall_improvement"
        )
        
        # Update final article
        state.final_article = refinement_result.get('refined_content', state.final_article)
        
        return {
            "session_id": session_id,
            "status": "final_article_refined", 
            "final_article": state.final_article,
            "changes_made": refinement_result.get('changes_made', ''),
            "word_count": refinement_result.get('word_count', 0),
            "in_final_refinement": True,
            "requires_feedback": True
        }
    
    async def complete_article(self, session_id: str) -> Dict[str, Any]:
        """Mark article as completed and prepare for download"""
        if session_id not in self.active_generations:
            raise ValueError(f"Session {session_id} not found")
        
        state = self.active_generations[session_id]
        
        if not state.final_article:
            raise ValueError("No final article available")
        
        # Update state to completed
        state.current_phase = GenerationPhase.COMPLETED
        state.final_refinement_mode = False
        
        # Generate download metadata
        total_words = sum(section.word_count for section in state.sections.values())
        
        return {
            "session_id": session_id,
            "status": "completed",
            "phase": GenerationPhase.COMPLETED,
            "final_article": state.final_article,
            "download_ready": True,
            "article_metadata": {
                "title": state.outline.title if state.outline else f"Article: {state.topic}",
                "topic": state.topic,
                "total_words": total_words,
                "sections_count": len(state.sections),
                "generated_at": datetime.now().isoformat(),
                "session_id": session_id
            },
            "message": "Article completed successfully! Ready for download."
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
        
        # Add title
        if state.outline and state.outline.title:
            final_content.append(f"# {state.outline.title}\n\n")
        
        # Add all approved sections in order
        for section_data in state.outline.sections:
            section_id = section_data.get("id")
            if section_id in state.sections:
                section = state.sections[section_id]
                final_content.append(f"## {section.title}\n\n{section.content}\n\n")
        
        final_article = "".join(final_content)
        total_words = sum(section.word_count for section in state.sections.values())
        
        # Update state
        state.current_phase = GenerationPhase.COMPLETED
        
        return {
            "session_id": session_id,
            "phase": GenerationPhase.COMPLETED,
            "status": "completed",
            "final_article": final_article,
            "total_words": total_words,
            "sections_count": len(state.sections),
            "topic": state.topic
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
            "generation_history": len(state.generation_history)
        }
    
    def cleanup_session(self, session_id: str):
        """Clean up completed session"""
        if session_id in self.active_generations:
            del self.active_generations[session_id]
            logger.info(f"🧹 Cleaned up session: {session_id}")