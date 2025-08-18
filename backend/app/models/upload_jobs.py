"""
Upload job models for batch document processing
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseModel


class JobStatus(str, Enum):
    """Upload job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadJob(BaseModel):
    """Upload job for batch document processing"""
    __tablename__ = "upload_jobs"
    
    collection_id = Column(Integer, ForeignKey("kb_collections.id"), nullable=False)
    job_id = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, default=JobStatus.PENDING)
    
    # Progress tracking
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    successful_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Job metadata
    upload_path = Column(String(500), nullable=True)  # Original upload path
    folder_structure = Column(JSON, nullable=True)    # Folder hierarchy
    file_list = Column(JSON, nullable=True)          # List of files to process
    error_log = Column(JSON, nullable=True)          # Detailed error information
    
    # Configuration
    max_file_size_mb = Column(Integer, default=10)
    preserve_structure = Column(Boolean, default=True)
    skip_unsupported = Column(Boolean, default=True)
    
    # Relationship
    collection = relationship("KBCollection", back_populates="upload_jobs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "collection_id": self.collection_id,
            "status": self.status,
            "progress": {
                "total_files": self.total_files,
                "processed_files": self.processed_files,
                "successful_files": self.successful_files,
                "failed_files": self.failed_files,
                "percentage": round(
                    # During processing, show progress based on processed files
                    # When completed, show success rate based on successful files
                    (self.processed_files / self.total_files * 100) if (self.status == "processing" and self.total_files > 0)
                    else (self.successful_files / self.total_files * 100) if self.total_files > 0
                    else 0, 1
                )
            },
            "timestamps": {
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration_seconds": (
                    (self.completed_at - self.started_at).total_seconds() 
                    if self.completed_at and self.started_at else None
                )
            },
            "metadata": {
                "upload_path": self.upload_path,
                "folder_structure": self.folder_structure,
                "preserve_structure": self.preserve_structure,
                "skip_unsupported": self.skip_unsupported
            },
            "errors": self.error_log or []
        }