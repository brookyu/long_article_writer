"""
Upload job management service for coordinating batch processing
"""

import asyncio
import json
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import shutil

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func

from app.models.upload_jobs import UploadJob, JobStatus
from app.models.knowledge_base import KBCollection
from app.services.batch_processor import batch_processor, BatchProcessingError, FileInfo

logger = logging.getLogger(__name__)


class UploadManager:
    """Manages upload jobs and coordinates batch processing"""
    
    def __init__(self):
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.temp_dir = Path(tempfile.gettempdir()) / "long_article_uploads"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def create_upload_job(
        self,
        collection_id: int,
        upload_type: str,  # 'folder', 'zip', 'multiple_files'
        file_paths: List[str] = None,
        folder_path: str = None,
        zip_path: str = None,
        preserve_structure: bool = True,
        skip_unsupported: bool = True,
        max_file_size_mb: int = 10,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Create a new upload job"""
        
        try:
            # Verify collection exists
            collection = await db.execute(
                select(KBCollection).where(KBCollection.id == collection_id)
            )
            if not collection.scalar_one_or_none():
                raise ValueError(f"Collection {collection_id} not found")
            
            # Generate unique job ID
            job_id = f"upload_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            # Create upload job record
            upload_job = UploadJob(
                collection_id=collection_id,
                job_id=job_id,
                status=JobStatus.PENDING,
                preserve_structure=preserve_structure,
                skip_unsupported=skip_unsupported,
                max_file_size_mb=max_file_size_mb
            )
            
            if upload_type == "folder" and folder_path:
                upload_job.upload_path = folder_path
            elif upload_type == "zip" and zip_path:
                upload_job.upload_path = zip_path
            elif upload_type == "multiple_files" and file_paths:
                upload_job.file_list = file_paths
            
            db.add(upload_job)
            await db.commit()
            await db.refresh(upload_job)
            
            logger.info(f"Created upload job {job_id} for collection {collection_id}")
            
            return {
                "job_id": job_id,
                "status": "created",
                "collection_id": collection_id,
                "upload_type": upload_type,
                "message": f"Upload job {job_id} created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create upload job: {e}")
            raise BatchProcessingError(f"Failed to create upload job: {e}")
    
    async def start_processing_job(
        self,
        job_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Start processing an upload job"""
        
        try:
            # Get job from database
            result = await db.execute(
                select(UploadJob).where(UploadJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            if job.status != JobStatus.PENDING:
                raise ValueError(f"Job {job_id} is not in pending status (current: {job.status})")
            
            # Update job status to processing
            job.status = JobStatus.PROCESSING
            job.started_at = func.now()
            await db.commit()
            
            # Start processing task
            task = asyncio.create_task(
                self._process_job_async(job_id, db)
            )
            self.active_jobs[job_id] = task
            
            logger.info(f"Started processing job {job_id}")
            
            return {
                "job_id": job_id,
                "status": "processing",
                "message": f"Job {job_id} processing started"
            }
            
        except Exception as e:
            # Update job status to failed
            try:
                await db.execute(
                    update(UploadJob)
                    .where(UploadJob.job_id == job_id)
                    .values(status=JobStatus.FAILED)
                )
                await db.commit()
            except:
                pass
            
            logger.error(f"Failed to start job {job_id}: {e}")
            raise BatchProcessingError(f"Failed to start job: {e}")
    
    async def _process_job_async(self, job_id: str, original_db: AsyncSession):
        """Process job asynchronously with its own database session"""
        
        from app.core.database import get_db
        
        # Create a new database session for this async task
        async for db in get_db():
            try:
                # Get job details
                result = await db.execute(
                    select(UploadJob).where(UploadJob.job_id == job_id)
                )
                job = result.scalar_one_or_none()
                
                if not job:
                    raise ValueError(f"Job {job_id} not found")
                
                # Determine processing path based on upload type
            if job.upload_path:
                upload_path = Path(job.upload_path)
                
                if upload_path.suffix.lower() == '.zip':
                    # Handle ZIP file
                    temp_extract_dir = self.temp_dir / job_id
                    temp_extract_dir.mkdir(exist_ok=True)
                    
                    try:
                        extracted_path = await batch_processor.extract_zip_folder(
                            upload_path, temp_extract_dir
                        )
                        files, folder_structure = await batch_processor.scan_folder_structure(
                            extracted_path, max_files=1000
                        )
                    finally:
                        # Cleanup temp directory
                        if temp_extract_dir.exists():
                            shutil.rmtree(temp_extract_dir)
                else:
                    # Handle folder
                    files, folder_structure = await batch_processor.scan_folder_structure(
                        upload_path, max_files=1000
                    )
            
            elif job.file_list:
                # Handle multiple individual files
                files = []
                folder_structure = {
                    "root": "multiple_files",
                    "total_size": 0,
                    "folders": [],
                    "file_types": {},
                    "errors": []
                }
                
                for file_path in job.file_list:
                    path = Path(file_path)
                    if path.exists():
                        file_size = path.stat().st_size
                        files.append(
                            FileInfo(
                                path=path,
                                relative_path=path.name,
                                size=file_size
                            )
                        )
                        folder_structure["total_size"] += file_size
            
            else:
                raise ValueError("No upload path or file list specified")
            
            # Update job with file count and structure
            job.total_files = len(files)
            job.folder_structure = folder_structure
            await db.commit()
            
            if len(files) == 0:
                job.status = JobStatus.COMPLETED
                job.completed_at = func.now()
                await db.commit()
                return
            
            # Process files with progress callback
            async def progress_callback(processed: int, total: int, last_result: Dict):
                await batch_processor._update_job_progress(
                    job_id, processed, 
                    last_result.get("successful_count", 0),
                    last_result.get("failed_count", 0),
                    db
                )
            
            # Process the batch
            results = await batch_processor.process_file_batch(
                files, job.collection_id, job_id, db, progress_callback
            )
            
            # Update final job status
            job.status = JobStatus.COMPLETED
            job.completed_at = func.now()
            job.processed_files = results["total_processed"]
            job.successful_files = len(results["successful"])
            job.failed_files = len(results["failed"])
            
            if results["errors"]:
                job.error_log = results["errors"]
            
            await db.commit()
            
            logger.info(f"Completed job {job_id}: {len(results['successful'])} successful, "
                       f"{len(results['failed'])} failed")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            
            # Update job status to failed
            try:
                await db.execute(
                    update(UploadJob)
                    .where(UploadJob.job_id == job_id)
                    .values(
                        status=JobStatus.FAILED,
                        completed_at=func.now(),
                        error_log=[{"error": str(e), "timestamp": datetime.now().isoformat()}]
                    )
                )
                await db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to update job status: {commit_error}")
        
        finally:
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    async def get_job_status(self, job_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get current status of an upload job"""
        
        try:
            result = await db.execute(
                select(UploadJob).where(UploadJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            return job.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            raise BatchProcessingError(f"Failed to get job status: {e}")
    
    async def cancel_job(self, job_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Cancel an upload job"""
        
        try:
            # Cancel active task if running
            if job_id in self.active_jobs:
                task = self.active_jobs[job_id]
                task.cancel()
                del self.active_jobs[job_id]
            
            # Update job status
            await db.execute(
                update(UploadJob)
                .where(UploadJob.job_id == job_id)
                .values(
                    status=JobStatus.CANCELLED,
                    completed_at=func.now()
                )
            )
            await db.commit()
            
            logger.info(f"Cancelled job {job_id}")
            
            return {
                "job_id": job_id,
                "status": "cancelled",
                "message": f"Job {job_id} cancelled successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise BatchProcessingError(f"Failed to cancel job: {e}")
    
    async def list_jobs(
        self,
        collection_id: Optional[int] = None,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """List upload jobs with optional filtering"""
        
        try:
            query = select(UploadJob).order_by(UploadJob.created_at.desc())
            
            if collection_id:
                query = query.where(UploadJob.collection_id == collection_id)
            
            if status:
                query = query.where(UploadJob.status == status)
            
            query = query.limit(limit)
            
            result = await db.execute(query)
            jobs = result.scalars().all()
            
            return {
                "jobs": [job.to_dict() for job in jobs],
                "total": len(jobs),
                "active_jobs": list(self.active_jobs.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            raise BatchProcessingError(f"Failed to list jobs: {e}")


# Global upload manager instance
upload_manager = UploadManager()