"""
Batch processing engine for folder uploads and multiple document processing
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
import uuid

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.upload_jobs import UploadJob, JobStatus
from app.models.knowledge_base import KBDocument, DocumentStatus, KBCollection
from app.models.folder_hierarchy import FolderNode, FolderHierarchyService
from app.services.text_processing import document_analyzer
from app.services.ollama_client import ollama_client
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class BatchProcessingError(Exception):
    """Custom exception for batch processing errors"""
    pass


class FileInfo:
    """File information for batch processing with folder hierarchy support"""
    def __init__(self, path: Path, relative_path: str, size: int, mime_type: str = None):
        self.path = path
        self.relative_path = relative_path
        self.size = size
        self.mime_type = mime_type
        self.parent_folder = str(path.parent.name) if path.parent.name != '.' else None
        
        # Enhanced folder hierarchy information
        self.folder_path = str(path.parent) if path.parent.name != '.' else ""
        if self.folder_path.startswith('/'):
            # Remove leading slash for relative paths
            self.folder_path = self.folder_path[1:] if len(self.folder_path) > 1 else ""
        self.folder_depth = len([p for p in relative_path.split('/')[:-1] if p])
        self.folder_hierarchy = [p for p in relative_path.split('/')[:-1] if p]
        
        # Auto-generate metadata
        self.folder_metadata = self._generate_folder_metadata()
        self.document_tags = self._generate_document_tags()
        self.content_category = self._infer_content_category()
    
    def _generate_folder_metadata(self) -> dict:
        """Generate metadata based on folder structure"""
        metadata = {
            "folder_depth": self.folder_depth,
            "folder_hierarchy": self.folder_hierarchy,
            "is_nested": self.folder_depth > 1,
            "folder_type": self._detect_folder_type()
        }
        
        if self.folder_hierarchy:
            metadata["root_folder"] = self.folder_hierarchy[0]
            metadata["immediate_parent"] = self.folder_hierarchy[-1] if self.folder_hierarchy else None
        
        return metadata
    
    def _generate_document_tags(self) -> list:
        """Generate tags based on file location and folder structure"""
        tags = []
        
        # Add folder-based tags
        for folder in self.folder_hierarchy:
            clean_folder = folder.lower().replace('_', '-').replace(' ', '-')
            if len(clean_folder) > 1:
                tags.append(f"folder:{clean_folder}")
        
        # Add depth-based tags
        if self.folder_depth == 0:
            tags.append("root-level")
        elif self.folder_depth == 1:
            tags.append("top-level")
        elif self.folder_depth > 3:
            tags.append("deeply-nested")
        
        # Add file extension tag
        file_ext = self.path.suffix.lower()
        if file_ext:
            tags.append(f"type:{file_ext[1:]}")  # Remove the dot
        
        return list(set(tags))
    
    def _detect_folder_type(self) -> str:
        """Detect the type of folder based on common patterns"""
        if not self.folder_hierarchy:
            return "root"
        
        folder_patterns = {
            "documentation": ["docs", "documentation", "wiki", "manual", "guide"],
            "source": ["src", "source", "code", "lib", "library"],
            "configuration": ["config", "conf", "settings", "env"],
            "data": ["data", "dataset", "csv", "json", "db"],
            "media": ["images", "img", "media", "assets", "pictures"],
            "test": ["test", "tests", "testing", "spec"],
            "examples": ["example", "examples", "demo", "sample"],
            "api": ["api", "rest", "graphql", "endpoints"],
            "templates": ["template", "templates", "layout", "theme"]
        }
        
        for folder in [f.lower() for f in self.folder_hierarchy]:
            for folder_type, patterns in folder_patterns.items():
                if any(pattern in folder for pattern in patterns):
                    return folder_type
        
        return "general"
    
    def _infer_content_category(self) -> str:
        """Infer content category from file and folder information"""
        file_ext = self.path.suffix.lower()
        folder_type = self._detect_folder_type()
        
        # File extension based categorization
        ext_categories = {
            "text": [".txt", ".md", ".rst", ".adoc"],
            "documentation": [".md", ".rst", ".adoc", ".wiki"],
            "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"],
            "data": [".json", ".csv", ".xml", ".yaml", ".yml"],
            "config": [".conf", ".ini", ".cfg", ".env", ".properties"],
            "web": [".html", ".htm", ".css", ".scss", ".less"],
            "office": [".pdf", ".doc", ".docx", ".rtf", ".odt"]
        }
        
        for category, extensions in ext_categories.items():
            if file_ext in extensions:
                return category
        
        # Fallback to folder type
        return folder_type if folder_type != "general" else "document"


class BatchProcessor:
    """Handles batch processing of multiple documents"""
    
    def __init__(self, max_concurrent_files: int = 3, max_file_size_mb: int = 500):
        self.max_concurrent_files = max_concurrent_files
        self.max_file_size_mb = max_file_size_mb
        self.supported_extensions = {
            '.txt', '.md', '.markdown', '.html', '.htm', 
            '.pdf', '.docx', '.doc', '.rtf', '.csv', '.json',
            '.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'
        }
    
    async def scan_folder_structure(
        self, 
        folder_path: Path, 
        max_files: int = 1000
    ) -> Tuple[List[FileInfo], Dict[str, Any]]:
        """
        Scan folder and return file list and structure metadata
        """
        files = []
        folder_structure = {
            "root": str(folder_path),
            "total_size": 0,
            "folders": [],
            "file_types": {},
            "errors": []
        }
        
        try:
            file_count = 0
            
            for root, dirs, filenames in os.walk(folder_path):
                current_path = Path(root)
                relative_root = current_path.relative_to(folder_path)
                
                # Track folders
                if str(relative_root) != '.':
                    folder_structure["folders"].append(str(relative_root))
                
                for filename in filenames:
                    if file_count >= max_files:
                        logger.warning(f"Maximum file limit ({max_files}) reached, skipping remaining files")
                        break
                    
                    file_path = current_path / filename
                    relative_path = file_path.relative_to(folder_path)
                    
                    # Skip hidden files and system files
                    if filename.startswith('.') or filename.startswith('~'):
                        continue
                    
                    try:
                        file_size = file_path.stat().st_size
                        file_ext = file_path.suffix.lower()
                        
                        # Check file size
                        if file_size > self.max_file_size_mb * 1024 * 1024:
                            folder_structure["errors"].append({
                                "file": str(relative_path),
                                "error": f"File too large: {file_size / (1024*1024):.1f}MB"
                            })
                            continue
                        
                        # Track file types
                        folder_structure["file_types"][file_ext] = folder_structure["file_types"].get(file_ext, 0) + 1
                        folder_structure["total_size"] += file_size
                        
                        # Add to file list if supported
                        if file_ext in self.supported_extensions:
                            files.append(FileInfo(
                                path=file_path,
                                relative_path=str(relative_path),
                                size=file_size
                            ))
                            file_count += 1
                        else:
                            folder_structure["errors"].append({
                                "file": str(relative_path),
                                "error": f"Unsupported file type: {file_ext}"
                            })
                    
                    except Exception as e:
                        folder_structure["errors"].append({
                            "file": str(relative_path),
                            "error": f"Error reading file: {str(e)}"
                        })
                
                if file_count >= max_files:
                    break
        
        except Exception as e:
            raise BatchProcessingError(f"Failed to scan folder: {e}")
        
        logger.info(f"Scanned folder: {len(files)} supported files, "
                   f"{len(folder_structure['errors'])} errors/skipped")
        
        return files, folder_structure
    
    async def extract_zip_folder(self, zip_path: Path, extract_to: Path) -> Path:
        """Extract ZIP file and return extraction path"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            # Find the main folder (handle case where ZIP has a single root folder)
            extracted_items = list(extract_to.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                return extracted_items[0]
            else:
                return extract_to
                
        except Exception as e:
            raise BatchProcessingError(f"Failed to extract ZIP file: {e}")
    
    async def process_file_batch_streaming(
        self,
        files: List[FileInfo],
        collection_id: int,
        job_id: str,
        db: AsyncSession,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of files with real-time streaming updates and folder structure preservation
        """
        results = {
            "successful": [],
            "failed": [],
            "total_processed": 0,
            "errors": [],
            "start_time": datetime.now(),
            "processing_times": [],
            "folder_structure": {
                "folders_created": 0,
                "hierarchy_depth": 0,
                "folder_paths": []
            }
        }
        
        # Update job status to processing
        await self._update_job_status(job_id, JobStatus.PROCESSING, db)
        
        # Create folder structure first
        try:
            folder_paths = list(set([file_info.folder_path for file_info in files if file_info.folder_path]))
            if folder_paths:
                logger.info(f"Creating folder structure with {len(folder_paths)} unique paths")
                created_folders = await FolderHierarchyService.create_folder_structure(
                    collection_id=collection_id,
                    folder_paths=folder_paths,
                    upload_job_id=None,  # Will be set later
                    db=db
                )
                
                results["folder_structure"]["folders_created"] = len(created_folders)
                results["folder_structure"]["folder_paths"] = folder_paths
                results["folder_structure"]["hierarchy_depth"] = max([f.folder_depth for f in files], default=0)
                
                logger.info(f"Created {len(created_folders)} folder nodes")
        except Exception as e:
            logger.error(f"Failed to create folder structure: {e}")
            # Continue processing even if folder creation fails
        
        # Create semaphore for concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        async def process_single_file_with_progress(file_info: FileInfo, index: int) -> Dict[str, Any]:
            async with semaphore:
                start_time = time.time()
                try:
                    # Send file start event
                    if progress_callback:
                        await progress_callback({
                            "type": "file_start",
                            "file": file_info.relative_path,
                            "index": index,
                            "total": len(files)
                        })
                    
                    result = await self._process_single_document(
                        file_info, collection_id, job_id, db
                    )
                    
                    processing_time = time.time() - start_time
                    result["processing_time"] = processing_time
                    
                    # Send file complete event
                    if progress_callback:
                        await progress_callback({
                            "type": "file_complete",
                            "file": file_info.relative_path,
                            "index": index,
                            "result": result,
                            "processing_time": processing_time
                        })
                    
                    return result
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    error_result = {
                        "file": file_info.relative_path,
                        "success": False,
                        "error": str(e),
                        "processing_time": processing_time
                    }
                    
                    # Send file error event
                    if progress_callback:
                        await progress_callback({
                            "type": "file_error",
                            "file": file_info.relative_path,
                            "index": index,
                            "error": str(e),
                            "processing_time": processing_time
                        })
                    
                    return error_result
        
        # Process files with progress tracking
        tasks = [
            process_single_file_with_progress(file_info, i) 
            for i, file_info in enumerate(files)
        ]
        
        # Process with real-time updates
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results["total_processed"] += 1
            results["processing_times"].append(result.get("processing_time", 0))
            
            if result["success"]:
                results["successful"].append(result["file"])
            else:
                results["failed"].append(result)
                results["errors"].append(result["error"])
            
            # Send progress update
            if progress_callback:
                await progress_callback({
                    "type": "batch_progress",
                    "processed": results["total_processed"],
                    "total": len(files),
                    "successful": len(results["successful"]),
                    "failed": len(results["failed"]),
                    "percentage": (results["total_processed"] / len(files)) * 100,
                    "avg_processing_time": sum(results["processing_times"]) / len(results["processing_times"]) if results["processing_times"] else 0
                })
            
            # Update job status in database
            await self._update_job_progress(
                job_id, results["total_processed"], 
                len(results["successful"]), len(results["failed"])
                # No db parameter - will use separate session
            )
        
        # Final job update
        results["end_time"] = datetime.now()
        results["total_time"] = (results["end_time"] - results["start_time"]).total_seconds()
        
        final_status = JobStatus.COMPLETED if len(results["failed"]) == 0 else JobStatus.FAILED
        await self._update_job_status(job_id, final_status, db)
        
        # Update folder statistics after processing
        try:
            await FolderHierarchyService.update_folder_statistics(collection_id, db)
            logger.info("Updated folder statistics after batch processing")
        except Exception as e:
            logger.error(f"Failed to update folder statistics: {e}")
        
        # Send completion event
        if progress_callback:
            await progress_callback({
                "type": "batch_complete",
                "results": results,
                "status": final_status.value
            })
        
        return results

    async def process_file_batch(
        self,
        files: List[FileInfo],
        collection_id: int,
        job_id: str,
        db: AsyncSession,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of files with progress tracking
        """
        results = {
            "successful": [],
            "failed": [],
            "total_processed": 0,
            "errors": []
        }
        
        # Create semaphore for concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        async def process_single_file(file_info: FileInfo) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await self._process_single_document(
                        file_info, collection_id, job_id
                    )
                except Exception as e:
                    logger.error(f"Failed to process {file_info.relative_path}: {e}")
                    return {
                        "file": file_info.relative_path,
                        "success": False,
                        "error": str(e)
                    }
        
        # Process files in batches
        tasks = [process_single_file(file_info) for file_info in files]
        
        # Process with progress updates
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results["total_processed"] += 1
            
            if result["success"]:
                results["successful"].append(result["file"])
            else:
                results["failed"].append(result)
                results["errors"].append(result["error"])
            
            # Update progress
            if progress_callback:
                await progress_callback(results["total_processed"], len(files), result)
            
            # Update job status in database periodically
            if results["total_processed"] % 5 == 0:  # Every 5 files
                await self._update_job_progress(
                    job_id, results["total_processed"], 
                    len(results["successful"]), len(results["failed"])
                    # No db parameter - will use separate session
                )
        
        return results
    
    async def _process_single_document(
        self,
        file_info: FileInfo,
        collection_id: int,
        job_id: str,
        db: AsyncSession = None  # Make db optional
    ) -> Dict[str, Any]:
        """Process a single document with its own database session"""
        from app.core.database import get_db
        
        # Use a separate database session for each document to avoid concurrency issues
        async for doc_db in get_db():
            try:
                # Check if file already exists (by hash)
                file_hash = await self._calculate_file_hash(file_info.path)
                
                existing_doc = await doc_db.execute(
                    select(KBDocument.id, KBDocument.filename).where(
                        KBDocument.collection_id == collection_id,
                        KBDocument.sha256 == file_hash
                    )
                )
                
                if existing_doc.scalar_one_or_none():
                    return {
                        "file": file_info.relative_path,
                        "success": True,
                        "skipped": True,
                        "reason": "Duplicate file (same hash)"
                    }
                
                # Create document record (only with columns that exist in current schema)
                document = KBDocument(
                    collection_id=collection_id,
                    filename=file_info.path.name,
                    original_filename=file_info.path.name,
                    size_bytes=file_info.size,
                    sha256=file_hash,
                    file_path=str(file_info.path),
                    mime_type=file_info.mime_type,
                    status=DocumentStatus.PROCESSING
                )
                
                doc_db.add(document)
                await doc_db.flush()  # Get document ID
            
                # Process document through pipeline
                from app.services.document_processor import DocumentProcessingPipeline
                doc_processor = DocumentProcessingPipeline()
                
                # Get user's embedding model
                embedding_model = await ollama_client.get_user_embedding_model(doc_db)
                
                processing_result = await doc_processor.process_document(
                    document_id=document.id,
                    collection_id=collection_id,
                    file_path=str(file_info.path),
                    mime_type=file_info.mime_type,
                    embedding_model=embedding_model,
                    db=doc_db
                )
                
                # Update document status
                document.status = DocumentStatus.COMPLETED
                document.chunk_count = processing_result.get("chunks_stored", 0)
                document.mime_type = processing_result.get("detected_mime_type")
                
                await doc_db.commit()
                
                return {
                    "file": file_info.relative_path,
                    "success": True,
                    "document_id": document.id,
                    "chunks": processing_result.get("chunks_stored", 0),
                    "processing_time": processing_result.get("processing_time_seconds", 0)
                }
                
            except Exception as e:
                # Update document status to failed if it was created
                if 'document' in locals():
                    try:
                        document.status = DocumentStatus.FAILED
                        document.error_message = str(e)
                        await doc_db.commit()
                    except Exception as commit_error:
                        logger.error(f"Failed to update document status on error: {commit_error}")
                        await doc_db.rollback()
                
                return {
                    "file": file_info.relative_path,
                    "success": False,
                    "error": str(e)
                }
            finally:
                # Database session automatically closed by async for
                break
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _update_job_progress(
        self,
        job_id: str,
        processed: int,
        successful: int,
        failed: int,
        db: AsyncSession = None  # db parameter now optional
    ):
        """Update job progress in database using a separate session"""
        from app.core.database import get_db
        
        # Use a separate database session for progress updates to avoid transaction conflicts
        async for progress_db in get_db():
            try:
                await progress_db.execute(
                    update(UploadJob)
                    .where(UploadJob.job_id == job_id)
                    .values(
                        processed_files=processed,
                        successful_files=successful,  # Fix: successful_files column DOES exist in schema
                        failed_files=failed
                    )
                )
                await progress_db.commit()
                logger.debug(f"Updated job {job_id} progress: {processed} processed, {successful} successful, {failed} failed")
            except Exception as e:
                logger.error(f"Failed to update job progress: {e}")
                await progress_db.rollback()
            finally:
                # Session is automatically closed by async for
                break
    
    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        db: AsyncSession,
        error_details: Optional[Dict] = None
    ):
        """Update job status in database"""
        try:
            update_values = {"status": status}
            
            if status == JobStatus.PROCESSING:
                update_values["start_time"] = datetime.now()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                update_values["end_time"] = datetime.now()
                
            if error_details:
                update_values["error_details"] = error_details
            
            await db.execute(
                update(UploadJob)
                .where(UploadJob.job_id == job_id)
                .values(**update_values)
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")


# Global batch processor instance
batch_processor = BatchProcessor()