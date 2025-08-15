from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response"""
    id: int
    collection_id: int
    filename: str
    original_filename: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: str
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Schema for listing documents"""
    documents: List[DocumentUploadResponse]
    total: int


class DocumentProcessingStatus(BaseModel):
    """Schema for document processing status"""
    id: int
    status: DocumentStatus
    progress: Optional[float] = None  # 0.0 to 1.0
    message: Optional[str] = None
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None