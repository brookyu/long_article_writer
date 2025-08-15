"""
Article generation schemas
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class OutlineRequest(BaseModel):
    """Request schema for outline generation"""
    collection_id: int = Field(..., description="Knowledge base collection ID")
    topic: str = Field(..., min_length=1, description="Main article topic")
    subtopics: Optional[List[str]] = Field(default=None, description="Optional subtopics to research")
    article_type: Literal["comprehensive", "tutorial", "analysis", "overview", "technical"] = Field(
        default="comprehensive", 
        description="Type of article to generate"
    )
    target_length: Literal["short", "medium", "long"] = Field(
        default="medium", 
        description="Target article length"
    )


class ArticleRequest(BaseModel):
    """Request schema for article generation"""
    collection_id: int = Field(..., description="Knowledge base collection ID")
    topic: str = Field(..., min_length=1, description="Main article topic")
    subtopics: Optional[List[str]] = Field(default=None, description="Optional subtopics to research")
    article_type: Literal["comprehensive", "tutorial", "analysis", "overview", "technical"] = Field(
        default="comprehensive", 
        description="Type of article to generate"
    )
    target_length: Literal["short", "medium", "long"] = Field(
        default="medium", 
        description="Target article length"
    )
    writing_style: Literal["professional", "conversational", "academic", "technical", "casual"] = Field(
        default="professional", 
        description="Writing style for the article"
    )


class ArticleSection(BaseModel):
    """Article section schema"""
    title: str
    content: str
    word_count: int
    citations: Optional[List[str]] = None


class ArticleResponse(BaseModel):
    """Response schema for generated articles"""
    id: Optional[int] = None
    title: str
    topic: str
    content: str
    sections: List[ArticleSection]
    word_count: int
    collection_id: int
    article_type: str
    target_length: str
    writing_style: str
    status: Literal["drafting", "completed", "failed"]
    progress: Optional[str] = None
    generated_at: str
    research_summary: Optional[dict] = None


class RefinementRequest(BaseModel):
    """Request schema for section refinement"""
    collection_id: int
    section_title: str
    current_content: str
    instructions: str = Field(..., min_length=1, description="Refinement instructions")


class ExportRequest(BaseModel):
    """Request schema for article export"""
    title: str
    content: str
    topic: str
    collection_id: int
    metadata: Optional[dict] = None


class StreamMessage(BaseModel):
    """Streaming message schema"""
    type: Literal["status", "research", "outline", "title", "content", "complete", "error", "refined_content"]
    message: Optional[str] = None
    data: Optional[dict] = None
    step: Optional[int] = None
    total_steps: Optional[int] = None
    section: Optional[int] = None
    total_sections: Optional[int] = None