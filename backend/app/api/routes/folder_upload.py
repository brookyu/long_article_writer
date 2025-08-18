"""
Folder upload API endpoints for batch document processing
"""

import logging
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import json
import asyncio

from app.core.database import get_db
from app.models.upload_jobs import JobStatus
from app.services.upload_manager import upload_manager
from app.services.batch_processor import BatchProcessingError

router = APIRouter()
logger = logging.getLogger(__name__)


class FolderUploadRequest(BaseModel):
    """Request model for folder upload"""
    preserve_structure: bool = True
    skip_unsupported: bool = True
    max_file_size_mb: int = 10


class BatchUploadRequest(BaseModel):
    """Request model for multiple file upload"""
    file_paths: List[str]
    preserve_structure: bool = False
    skip_unsupported: bool = True
    max_file_size_mb: int = 10


@router.post("/{collection_id}/upload-folder/")
async def upload_folder_zip(
    collection_id: int,
    background_tasks: BackgroundTasks,
    zip_file: UploadFile = File(...),
    preserve_structure: bool = Form(True),
    skip_unsupported: bool = Form(True),
    max_file_size_mb: int = Form(500),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a ZIP file containing a folder structure
    
    The ZIP file will be extracted and all supported documents will be processed
    """
    
    try:
        # Validate file type
        if not zip_file.filename.lower().endswith('.zip'):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Only ZIP files are supported for folder upload"
            )
        
        # Save uploaded ZIP file temporarily
        temp_dir = Path(tempfile.gettempdir()) / "folder_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        zip_path = temp_dir / f"{collection_id}_{zip_file.filename}"
        
        try:
            # Save uploaded file
            with open(zip_path, "wb") as f:
                shutil.copyfileobj(zip_file.file, f)
            
            # Create upload job
            job_result = await upload_manager.create_upload_job(
                collection_id=collection_id,
                upload_type="zip",
                zip_path=str(zip_path),
                preserve_structure=preserve_structure,
                skip_unsupported=skip_unsupported,
                max_file_size_mb=max_file_size_mb,
                db=db
            )
            
            # Start processing in background
            background_tasks.add_task(
                _start_job_processing,
                job_result["job_id"]
            )
            
            return JSONResponse(
                status_code=HTTPStatus.ACCEPTED,
                content={
                    "job_id": job_result["job_id"],
                    "status": "accepted",
                    "message": "Folder upload started. Use job_id to track progress.",
                    "collection_id": collection_id,
                    "filename": zip_file.filename
                }
            )
            
        finally:
            # Cleanup will happen after processing
            pass
            
    except BatchProcessingError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Folder upload failed: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Folder upload failed: {str(e)}"
        )


@router.post("/{collection_id}/upload-batch/")
async def upload_multiple_files(
    collection_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    preserve_structure: bool = Form(False),
    skip_unsupported: bool = Form(True),
    max_file_size_mb: int = Form(500),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload multiple files at once
    
    All files will be processed as a batch job
    """
    
    try:
        if len(files) > 100:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Maximum 100 files allowed per batch upload"
            )
        
        # Save uploaded files temporarily
        temp_dir = Path(tempfile.gettempdir()) / "batch_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        job_temp_dir = temp_dir / f"job_{collection_id}_{int(datetime.now().timestamp())}"
        job_temp_dir.mkdir()
        
        file_paths = []
        
        try:
            # Save all uploaded files
            for file in files:
                if file.filename:
                    # Sanitize filename to avoid filesystem issues
                    safe_filename = file.filename.replace(":", "_").replace("/", "_").replace("\\", "_")
                    # Ensure filename is not empty after sanitization
                    if not safe_filename.strip():
                        safe_filename = f"file_{int(datetime.now().timestamp())}"
                    
                    file_path = job_temp_dir / safe_filename
                    with open(file_path, "wb") as f:
                        shutil.copyfileobj(file.file, f)
                    file_paths.append(str(file_path))
            
            # Create upload job
            job_result = await upload_manager.create_upload_job(
                collection_id=collection_id,
                upload_type="multiple_files",
                file_paths=file_paths,
                preserve_structure=preserve_structure,
                skip_unsupported=skip_unsupported,
                max_file_size_mb=max_file_size_mb,
                db=db
            )
            
            # Start processing in background
            background_tasks.add_task(
                _start_job_processing,
                job_result["job_id"]
            )
            
            return JSONResponse(
                status_code=HTTPStatus.ACCEPTED,
                content={
                    "job_id": job_result["job_id"],
                    "status": "accepted",
                    "message": f"Batch upload started with {len(files)} files. Use job_id to track progress.",
                    "collection_id": collection_id,
                    "file_count": len(files)
                }
            )
            
        except Exception as e:
            # Cleanup temp files on error
            if job_temp_dir.exists():
                shutil.rmtree(job_temp_dir)
            raise e
            
    except BatchProcessingError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Batch upload failed: {str(e)}"
        )


@router.get("/{collection_id}/upload-jobs/{job_id}/status/")
async def get_upload_job_status(
    collection_id: int,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the status of an upload job"""
    
    try:
        job_status = await upload_manager.get_job_status(job_id, db)
        
        # Verify job belongs to collection
        if job_status["collection_id"] != collection_id:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Job not found for this collection"
            )
        
        return job_status
        
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=str(e)
        )
    except BatchProcessingError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/{collection_id}/upload-jobs/{job_id}/stream/")
async def stream_upload_progress(
    collection_id: int,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stream real-time progress updates for an upload job"""
    
    async def generate_progress_updates():
        """Generate Server-Sent Events for job progress"""
        try:
            # Verify job exists and belongs to collection
            job_status = await upload_manager.get_job_status(job_id, db)
            
            if job_status["collection_id"] != collection_id:
                yield f"data: {json.dumps({'error': 'Job not found for this collection'})}\n\n"
                return
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'job_status', 'data': job_status})}\n\n"
            
            # If job is already completed/failed, send final status and close
            if job_status["status"] in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                yield f"data: {json.dumps({'type': 'job_complete', 'data': job_status})}\n\n"
                return
            
            # Stream live updates while job is processing
            last_processed = job_status.get("processed_files", 0)
            
            while True:
                try:
                    # Get current job status
                    current_status = await upload_manager.get_job_status(job_id, db)
                    
                    # Send update if progress changed
                    if current_status.get("processed_files", 0) != last_processed:
                        yield f"data: {json.dumps({'type': 'progress_update', 'data': current_status})}\n\n"
                        last_processed = current_status.get("processed_files", 0)
                    
                    # Check if job completed
                    if current_status["status"] in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                        yield f"data: {json.dumps({'type': 'job_complete', 'data': current_status})}\n\n"
                        break
                    
                    # Wait before next check
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    break
                    
        except Exception as e:
            logger.error(f"Stream error for job {job_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_progress_updates(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


@router.delete("/{collection_id}/upload-jobs/{job_id}/")
async def cancel_upload_job(
    collection_id: int,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel an upload job"""
    
    try:
        # First verify job exists and belongs to collection
        job_status = await upload_manager.get_job_status(job_id, db)
        
        if job_status["collection_id"] != collection_id:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Job not found for this collection"
            )
        
        if job_status["status"] in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Cannot cancel job in {job_status['status']} status"
            )
        
        result = await upload_manager.cancel_job(job_id, db)
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=str(e)
        )
    except BatchProcessingError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/{collection_id}/upload-jobs/")
async def list_upload_jobs(
    collection_id: int,
    status: Optional[JobStatus] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List upload jobs for a collection"""
    
    try:
        jobs = await upload_manager.list_jobs(
            collection_id=collection_id,
            status=status,
            limit=limit,
            db=db
        )
        
        return jobs
        
    except BatchProcessingError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/formats/supported/")
async def get_supported_formats():
    """Get list of supported file formats"""
    
    from app.services.text_processing import DocumentProcessor
    
    processor = DocumentProcessor()
    extensions = processor.get_supported_extensions()
    
    return {
        "supported_extensions": extensions,
        "total_formats": len(extensions),
        "description": "Supported file formats for document upload and processing"
    }


# Background task helper
async def _start_job_processing(job_id: str):
    """Background task to start job processing"""
    from app.core.database import get_db
    
    # Create a new database session for this background task
    async for db in get_db():
        try:
            await upload_manager.start_processing_job(job_id, db)
            break  # Exit the async for loop after processing
        except Exception as e:
            logger.error(f"Failed to start job processing: {e}")
            break