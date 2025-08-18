"""
Simple Upload API
Inspired by Open WebUI's straightforward approach.
No complex job queues - direct processing with immediate feedback.
NOW WITH REAL-TIME STREAMING SUPPORT!
"""

import tempfile
import zipfile
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.knowledge_base import KBCollection
from app.services.simple_document_processor import SimpleDocumentProcessor
from sqlalchemy import select
import json
import asyncio
import logging
import mimetypes

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/collections/{collection_id}/upload-simple/")
async def upload_documents_simple(
    collection_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Simple document upload endpoint inspired by Open WebUI.
    Processes files immediately and returns results.
    """
    try:
        # Verify collection exists
        collection = await db.execute(
            select(KBCollection).where(KBCollection.id == collection_id)
        )
        collection = collection.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        processor = SimpleDocumentProcessor()
        results = []
        
        # Process each file immediately
        for upload_file in files:
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{upload_file.filename}") as temp_file:
                    content = await upload_file.read()
                    temp_file.write(content)
                    temp_file_path = Path(temp_file.name)
                
                # Process the document
                result = await processor.process_document(
                    file_path=temp_file_path,
                    collection_id=collection_id,
                    db=db,
                    original_filename=upload_file.filename
                )
                
                results.append(result)
                
                # Cleanup temp file
                temp_file_path.unlink(missing_ok=True)
                
            except Exception as e:
                logger.error(f"Failed to process {upload_file.filename}: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "filename": upload_file.filename
                })
        
        # Summary
        successful = [r for r in results if r["success"] and not r.get("skipped")]
        failed = [r for r in results if not r["success"]]
        skipped = [r for r in results if r.get("skipped")]
        
        return {
            "message": f"Processed {len(files)} files",
            "summary": {
                "total": len(files),
                "successful": len(successful),
                "failed": len(failed),
                "skipped": len(skipped)
            },
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections/{collection_id}/upload-stream/")
async def upload_documents_stream(
    collection_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    🚀 STREAMING UPLOAD ENDPOINT 🚀
    Real-time progress updates for file uploads!
    Perfect for your 70-file upload with live progress bars.
    """
    
    async def stream_upload_progress():
        try:
            # Verify collection exists
            collection = await db.execute(
                select(KBCollection).where(KBCollection.id == collection_id)
            )
            collection = collection.scalar_one_or_none()
            
            if not collection:
                yield f'data: {json.dumps({"type": "error", "message": "Collection not found"})}\n\n'
                return
            
            # Send initial status
            total_files = len(files)
            yield f'data: {json.dumps({"type": "start", "message": f"Starting upload of {total_files} files", "total_files": total_files})}\n\n'
            
            processor = SimpleDocumentProcessor()
            results = []
            processed_count = 0
            successful_count = 0
            failed_count = 0
            
            # Process each file with progress updates
            for i, upload_file in enumerate(files, 1):
                try:
                    # Send file start event
                    yield f'data: {json.dumps({"type": "file_start", "filename": upload_file.filename, "file_index": i, "total_files": total_files})}\n\n'
                    
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{upload_file.filename}") as temp_file:
                        content = await upload_file.read()
                        temp_file.write(content)
                        temp_file_path = Path(temp_file.name)
                    
                    # Determine MIME type
                    mime_type, _ = mimetypes.guess_type(upload_file.filename)
                    
                    # Process the document
                    result = await processor.process_document(
                        file_path=temp_file_path,
                        collection_id=collection_id,
                        db=db,
                        original_filename=upload_file.filename,
                        mime_type=mime_type
                    )
                    
                    results.append(result)
                    processed_count += 1
                    
                    if result["success"] and not result.get("skipped"):
                        successful_count += 1
                        yield f'data: {json.dumps({"type": "file_success", "filename": upload_file.filename, "file_index": i, "document_id": result.get("document_id"), "chunks_created": result.get("chunks_stored", 0)})}\n\n'
                    else:
                        failed_count += 1
                        yield f'data: {json.dumps({"type": "file_failed", "filename": upload_file.filename, "file_index": i, "error": result.get("error", "Unknown error")})}\n\n'
                    
                    # Cleanup temp file
                    temp_file_path.unlink(missing_ok=True)
                    
                    # Send progress update
                    progress_percentage = (processed_count / total_files) * 100
                    yield f'data: {json.dumps({"type": "progress", "processed": processed_count, "successful": successful_count, "failed": failed_count, "total": total_files, "percentage": progress_percentage})}\n\n'
                    
                    # Small delay to make progress visible
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process {upload_file.filename}: {e}")
                    failed_count += 1
                    processed_count += 1
                    
                    results.append({
                        "success": False,
                        "error": str(e),
                        "filename": upload_file.filename
                    })
                    
                    yield f'data: {json.dumps({"type": "file_failed", "filename": upload_file.filename, "file_index": i, "error": str(e)})}\n\n'
                    
                    # Send progress update even for failed files
                    progress_percentage = (processed_count / total_files) * 100
                    yield f'data: {json.dumps({"type": "progress", "processed": processed_count, "successful": successful_count, "failed": failed_count, "total": total_files, "percentage": progress_percentage})}\n\n'
            
            # Send final completion event
            final_summary = {
                "total": total_files,
                "successful": successful_count,
                "failed": failed_count,
                "skipped": len([r for r in results if r.get("skipped")])
            }
            
            yield f'data: {json.dumps({"type": "complete", "message": f"Upload complete! {successful_count}/{total_files} files processed successfully", "summary": final_summary, "results": results})}\n\n'
            
        except Exception as e:
            logger.error(f"Streaming upload failed: {e}")
            yield f'data: {json.dumps({"type": "error", "message": f"Upload failed: {str(e)}"})}\n\n'
    
    return StreamingResponse(
        stream_upload_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.post("/collections/{collection_id}/upload-folder-simple/")
async def upload_folder_simple(
    collection_id: int,
    zipFile: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Simple folder upload with streaming progress.
    Inspired by Open WebUI's approach but with real-time feedback.
    """
    try:
        # Verify collection exists
        collection = await db.execute(
            select(KBCollection).where(KBCollection.id == collection_id)
        )
        collection = collection.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Extract zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Save uploaded zip
            zip_path = temp_dir_path / "upload.zip"
            with open(zip_path, "wb") as f:
                content = await zipFile.read()
                f.write(content)
            
            # Extract files
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir_path)
            
            # Find all supported files
            supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.doc', '.html', '.csv'}
            file_paths = []
            
            for file_path in temp_dir_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    file_paths.append(file_path)
            
            if not file_paths:
                return {
                    "message": "No supported files found in zip",
                    "summary": {"total": 0, "successful": 0, "failed": 0, "skipped": 0},
                    "results": []
                }
            
            # Process files with simple progress tracking
            processor = SimpleDocumentProcessor()
            results = await processor.process_multiple_documents(
                file_paths=file_paths,
                collection_id=collection_id,
                db=db
            )
            
            return {
                "message": f"Processed {results['total']} files from folder",
                "summary": {
                    "total": results["total"],
                    "successful": len(results["successful"]),
                    "failed": len(results["failed"]),
                    "skipped": len(results["skipped"])
                },
                "results": results["successful"] + results["failed"] + results["skipped"]
            }
            
    except Exception as e:
        logger.error(f"Folder upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collections/{collection_id}/upload-folder-stream/")
async def upload_folder_stream(
    collection_id: int,
    zipFile: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    🚀 STREAMING FOLDER UPLOAD ENDPOINT 🚀
    Real-time progress updates for folder uploads!
    Perfect for your 70-file folder with live progress bars.
    """
    
    async def stream_folder_upload():
        try:
            # Verify collection exists
            collection = await db.execute(
                select(KBCollection).where(KBCollection.id == collection_id)
            )
            collection = collection.scalar_one_or_none()
            
            if not collection:
                yield f'data: {json.dumps({"type": "error", "message": "Collection not found"})}\n\n'
                return
            
            yield f'data: {json.dumps({"type": "start", "message": "Extracting files from ZIP..."})}\n\n'
            
            # Extract zip file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                
                # Save uploaded zip
                zip_path = temp_dir_path / "upload.zip"
                with open(zip_path, "wb") as f:
                    content = await zipFile.read()
                    f.write(content)
                
                # Extract files with proper encoding for Chinese filenames
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Extract files one by one with proper filename handling
                    for member in zip_ref.infolist():
                        if member.is_dir():
                            continue
                            
                        # Get the original filename as bytes and try different encodings
                        original_filename = member.filename
                        
                        try:
                            # Try different encoding approaches for Chinese filenames
                            if original_filename.encode('utf-8', errors='ignore') != original_filename.encode('latin1', errors='ignore'):
                                # Filename likely has encoding issues
                                try:
                                    # Try GBK decoding first (common for Chinese Windows)
                                    decoded_name = original_filename.encode('cp437').decode('gbk')
                                except (UnicodeDecodeError, UnicodeEncodeError):
                                    try:
                                        # Try UTF-8 decoding
                                        decoded_name = original_filename.encode('cp437').decode('utf-8')
                                    except (UnicodeDecodeError, UnicodeEncodeError):
                                        # Use original if all fail
                                        decoded_name = original_filename
                            else:
                                decoded_name = original_filename
                            
                            # Extract with corrected filename
                            member.filename = decoded_name
                            zip_ref.extract(member, temp_dir_path)
                            
                        except Exception as e:
                            logger.warning(f"Failed to extract {original_filename}: {e}")
                            # Try extracting with original filename as fallback
                            try:
                                member.filename = original_filename
                                zip_ref.extract(member, temp_dir_path)
                            except Exception as e2:
                                logger.error(f"Failed to extract {original_filename} with original name: {e2}")
                                continue
                
                # Find all supported files
                supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.doc', '.html', '.csv'}
                file_paths = []
                
                # Debug: List all extracted files
                logger.info(f"Listing all extracted files:")
                all_files = list(temp_dir_path.rglob('*'))
                for file_path in all_files:
                    if file_path.is_file():
                        logger.info(f"  Extracted file: {file_path.name} (extension: {file_path.suffix.lower()})")
                        if file_path.suffix.lower() in supported_extensions:
                            file_paths.append(file_path)
                            logger.info(f"    → Added to processing queue")
                
                logger.info(f"Total supported files found: {len(file_paths)}")
                
                if not file_paths:
                    yield f'data: {json.dumps({"type": "complete", "message": "No supported files found in ZIP", "summary": {"total": 0, "successful": 0, "failed": 0, "skipped": 0}})}\n\n'
                    return
                
                total_files = len(file_paths)
                yield f'data: {json.dumps({"type": "extraction_complete", "message": f"Found {total_files} supported files", "total_files": total_files})}\n\n'
                
                # Process files with streaming progress
                processor = SimpleDocumentProcessor()
                results = []
                processed_count = 0
                successful_count = 0
                failed_count = 0
                
                for i, file_path in enumerate(file_paths, 1):
                    try:
                        # Send file start event
                        yield f'data: {json.dumps({"type": "file_start", "filename": file_path.name, "file_index": i, "total_files": total_files})}\n\n'
                        
                        # Determine MIME type
                        mime_type, _ = mimetypes.guess_type(file_path.name)
                        
                        # Process the document
                        logger.info(f"Processing file: {file_path.name} (mime_type: {mime_type})")
                        result = await processor.process_document(
                            file_path=file_path,
                            collection_id=collection_id,
                            db=db,
                            original_filename=file_path.name,
                            mime_type=mime_type
                        )
                        logger.info(f"Process result for {file_path.name}: {result}")
                        
                        results.append(result)
                        processed_count += 1
                        
                        if result["success"] and not result.get("skipped"):
                            successful_count += 1
                            yield f'data: {json.dumps({"type": "file_success", "filename": file_path.name, "file_index": i, "document_id": result.get("document_id"), "chunks_created": result.get("chunks_stored", 0)})}\n\n'
                        elif result.get("skipped"):
                            # Handle skipped files (duplicates) - this shouldn't happen anymore since we replace duplicates
                            yield f'data: {json.dumps({"type": "file_skipped", "filename": file_path.name, "file_index": i, "reason": result.get("reason", "Document already exists")})}\n\n'
                        else:
                            failed_count += 1
                            yield f'data: {json.dumps({"type": "file_failed", "filename": file_path.name, "file_index": i, "error": result.get("error", "Unknown error")})}\n\n'
                        
                        # Send progress update
                        progress_percentage = (processed_count / total_files) * 100
                        yield f'data: {json.dumps({"type": "progress", "processed": processed_count, "successful": successful_count, "failed": failed_count, "total": total_files, "percentage": progress_percentage})}\n\n'
                        
                        # Small delay to make progress visible and prevent overwhelming Milvus
                        await asyncio.sleep(1.0)  # Increased delay for stability
                        
                    except Exception as e:
                        logger.error(f"Failed to process {file_path.name}: {e}")
                        failed_count += 1
                        processed_count += 1
                        
                        results.append({
                            "success": False,
                            "error": str(e),
                            "filename": file_path.name
                        })
                        
                        error_details = f"{type(e).__name__}: {str(e)}"
                        import traceback
                        full_traceback = traceback.format_exc()
                        logger.error(f"🔥 DETAILED ERROR for {file_path.name}: {error_details}")
                        logger.error(f"🔥 FULL TRACEBACK: {full_traceback}")
                        yield f'data: {json.dumps({"type": "file_failed", "filename": file_path.name, "file_index": i, "error": error_details, "error_type": type(e).__name__, "traceback": full_traceback[:500]})}\n\n'
                        
                        # Send progress update even for failed files
                        progress_percentage = (processed_count / total_files) * 100
                        yield f'data: {json.dumps({"type": "progress", "processed": processed_count, "successful": successful_count, "failed": failed_count, "total": total_files, "percentage": progress_percentage})}\n\n'
                
                # Send final completion event
                final_summary = {
                    "total": total_files,
                    "successful": successful_count,
                    "failed": failed_count,
                    "skipped": len([r for r in results if r.get("skipped")])
                }
                
                yield f'data: {json.dumps({"type": "complete", "message": f"Folder upload complete! {successful_count}/{total_files} files processed successfully", "summary": final_summary, "results": results})}\n\n'
                
        except Exception as e:
            logger.error(f"Streaming folder upload failed: {e}")
            yield f'data: {json.dumps({"type": "error", "message": f"Folder upload failed: {str(e)}"})}\n\n'
    
    return StreamingResponse(
        stream_folder_upload(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )