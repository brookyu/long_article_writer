"""
Pydantic schemas for knowledge base API requests and responses
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.knowledge_base import DocumentStatus


# Collection schemas
class CollectionCreate(BaseModel):
    """Schema for creating a new collection"""
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    embedding_model: Optional[str] = Field(default=None, description="Embedding model to use (uses settings if not specified)")


class CollectionUpdate(BaseModel):
    """Schema for updating a collection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    embedding_model: Optional[str] = Field(None, description="Embedding model to use")


class CollectionResponse(BaseModel):
    """Schema for collection responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    embedding_model: Optional[str] = None
    total_documents: int = 0
    total_chunks: int = 0
    created_at: datetime
    updated_at: datetime


class CollectionListResponse(BaseModel):
    """Schema for listing collections"""
    collections: List[CollectionResponse]
    total: int


# Document schemas
class DocumentResponse(BaseModel):
    """Schema for document responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    collection_id: int
    filename: str
    original_filename: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: str
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Schema for listing documents"""
    documents: List[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    document: DocumentResponse
    message: str


# Chunk schemas
class ChunkResponse(BaseModel):
    """Schema for chunk responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    document_id: int
    chunk_index: int
    text: str
    char_count: Optional[int] = None
    milvus_id: Optional[str] = None
    created_at: datetime


# Status and error schemas
class ProcessingStatus(BaseModel):
    """Schema for processing status updates"""
    document_id: int
    status: DocumentStatus
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = None
    error: Optional[str] = None


class APIError(BaseModel):
    """Schema for API error responses"""
    error: str
    message: str
    details: Optional[dict] = None