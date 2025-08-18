"""
Folder hierarchy API endpoints for managing document organization
"""

import logging
from typing import List, Optional
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.models.folder_hierarchy import FolderNode, FolderHierarchyService
from app.models.knowledge_base import KBDocument, KBCollection

router = APIRouter()
logger = logging.getLogger(__name__)


class FolderStatsResponse(BaseModel):
    """Response model for folder statistics"""
    total_folders: int
    total_documents: int
    total_size_bytes: int
    max_depth: int
    folder_types: dict
    content_categories: dict


class FolderSearchRequest(BaseModel):
    """Request model for folder search"""
    query: str
    include_documents: bool = False
    folder_type: Optional[str] = None
    content_category: Optional[str] = None
    min_depth: Optional[int] = None
    max_depth: Optional[int] = None


@router.get("/{collection_id}/folder-tree/")
async def get_folder_tree(
    collection_id: int,
    include_documents: bool = Query(False, description="Include document details in response"),
    folder_type: Optional[str] = Query(None, description="Filter by folder type"),
    max_depth: Optional[int] = Query(None, description="Maximum depth to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get the complete folder tree structure for a collection"""
    
    try:
        # Verify collection exists
        collection = await db.execute(
            select(KBCollection).where(KBCollection.id == collection_id)
        )
        if not collection.scalar_one_or_none():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Collection {collection_id} not found"
            )
        
        # Get folder tree
        folder_tree = await FolderHierarchyService.get_folder_tree(
            collection_id=collection_id,
            include_documents=include_documents,
            db=db
        )
        
        # Apply filters
        if folder_type or max_depth is not None:
            folder_tree = _filter_folder_tree(
                folder_tree, 
                folder_type=folder_type, 
                max_depth=max_depth
            )
        
        return {
            "collection_id": collection_id,
            "folder_tree": folder_tree,
            "total_folders": _count_folders_in_tree(folder_tree),
            "include_documents": include_documents
        }
        
    except Exception as e:
        logger.error(f"Failed to get folder tree: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to get folder tree: {str(e)}"
        )


@router.get("/{collection_id}/folder-stats/")
async def get_folder_statistics(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
) -> FolderStatsResponse:
    """Get comprehensive statistics about folder structure and content"""
    
    try:
        # Verify collection exists
        collection = await db.execute(
            select(KBCollection).where(KBCollection.id == collection_id)
        )
        if not collection.scalar_one_or_none():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Collection {collection_id} not found"
            )
        
        # Get folder statistics
        folder_stats = await db.execute(
            select(
                func.count(FolderNode.id),
                func.max(FolderNode.depth),
                func.sum(FolderNode.total_size_bytes)
            ).where(FolderNode.collection_id == collection_id)
        )
        total_folders, max_depth, total_size = folder_stats.one()
        
        # Get document count
        doc_count = await db.execute(
            select(func.count(KBDocument.id))
            .where(KBDocument.collection_id == collection_id)
        )
        total_documents = doc_count.scalar()
        
        # Get folder type distribution
        folder_types_result = await db.execute(
            select(FolderNode.folder_metadata)
            .where(FolderNode.collection_id == collection_id)
        )
        
        folder_types = {}
        content_categories = {}
        
        for (metadata,) in folder_types_result:
            if metadata and isinstance(metadata, dict):
                folder_type = metadata.get("folder_type", "unknown")
                folder_types[folder_type] = folder_types.get(folder_type, 0) + 1
        
        # Get content category distribution
        categories_result = await db.execute(
            select(KBDocument.content_category, func.count(KBDocument.id))
            .where(KBDocument.collection_id == collection_id)
            .group_by(KBDocument.content_category)
        )
        
        for category, count in categories_result:
            if category:
                content_categories[category] = count
        
        return FolderStatsResponse(
            total_folders=total_folders or 0,
            total_documents=total_documents or 0,
            total_size_bytes=total_size or 0,
            max_depth=max_depth or 0,
            folder_types=folder_types,
            content_categories=content_categories
        )
        
    except Exception as e:
        logger.error(f"Failed to get folder statistics: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to get folder statistics: {str(e)}"
        )


@router.get("/{collection_id}/folders/{folder_id}/")
async def get_folder_details(
    collection_id: int,
    folder_id: int,
    include_documents: bool = Query(True, description="Include documents in folder"),
    include_children: bool = Query(True, description="Include child folders"),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific folder"""
    
    try:
        # Get folder with relationships
        folder_result = await db.execute(
            select(FolderNode)
            .where(
                FolderNode.id == folder_id,
                FolderNode.collection_id == collection_id
            )
        )
        folder = folder_result.scalar_one_or_none()
        
        if not folder:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Folder {folder_id} not found in collection {collection_id}"
            )
        
        # Get folder data
        folder_data = folder.to_dict(
            include_children=include_children,
            include_documents=include_documents
        )
        
        # Add breadcrumb navigation
        folder_data["breadcrumb"] = folder.get_breadcrumb()
        
        # Get parent folder info if exists
        if folder.parent_id:
            parent_result = await db.execute(
                select(FolderNode.name, FolderNode.full_path)
                .where(FolderNode.id == folder.parent_id)
            )
            parent = parent_result.one_or_none()
            if parent:
                folder_data["parent"] = {
                    "id": folder.parent_id,
                    "name": parent.name,
                    "full_path": parent.full_path
                }
        
        return folder_data
        
    except Exception as e:
        logger.error(f"Failed to get folder details: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to get folder details: {str(e)}"
        )


@router.post("/{collection_id}/folders/search/")
async def search_folders(
    collection_id: int,
    search_request: FolderSearchRequest,
    limit: int = Query(50, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Search folders and their contents"""
    
    try:
        # Build search query
        query = select(FolderNode).where(FolderNode.collection_id == collection_id)
        
        # Add text search
        if search_request.query:
            search_term = f"%{search_request.query.lower()}%"
            query = query.where(
                FolderNode.name.ilike(search_term) |
                FolderNode.full_path.ilike(search_term) |
                FolderNode.content_summary.ilike(search_term)
            )
        
        # Add filters
        if search_request.folder_type:
            query = query.where(
                FolderNode.folder_metadata["folder_type"].astext == search_request.folder_type
            )
        
        if search_request.min_depth is not None:
            query = query.where(FolderNode.depth >= search_request.min_depth)
        
        if search_request.max_depth is not None:
            query = query.where(FolderNode.depth <= search_request.max_depth)
        
        # Apply limit and execute
        query = query.limit(limit)
        result = await db.execute(query)
        folders = result.scalars().all()
        
        # Convert to dict format
        folder_results = [
            folder.to_dict(
                include_children=False,
                include_documents=search_request.include_documents
            )
            for folder in folders
        ]
        
        return {
            "query": search_request.query,
            "filters": {
                "folder_type": search_request.folder_type,
                "content_category": search_request.content_category,
                "min_depth": search_request.min_depth,
                "max_depth": search_request.max_depth
            },
            "total_results": len(folder_results),
            "folders": folder_results
        }
        
    except Exception as e:
        logger.error(f"Failed to search folders: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to search folders: {str(e)}"
        )


@router.put("/{collection_id}/folders/{folder_id}/")
async def update_folder_metadata(
    collection_id: int,
    folder_id: int,
    metadata: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update folder metadata and tags"""
    
    try:
        # Get folder
        folder_result = await db.execute(
            select(FolderNode)
            .where(
                FolderNode.id == folder_id,
                FolderNode.collection_id == collection_id
            )
        )
        folder = folder_result.scalar_one_or_none()
        
        if not folder:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Folder {folder_id} not found"
            )
        
        # Update metadata
        if "folder_metadata" in metadata:
            folder.folder_metadata = {
                **(folder.folder_metadata or {}),
                **metadata["folder_metadata"]
            }
        
        if "auto_tags" in metadata:
            folder.auto_tags = metadata["auto_tags"]
        
        if "content_summary" in metadata:
            folder.content_summary = metadata["content_summary"]
        
        folder.last_updated = func.now()
        
        await db.commit()
        await db.refresh(folder)
        
        return folder.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to update folder metadata: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to update folder metadata: {str(e)}"
        )


@router.post("/{collection_id}/folders/rebuild-stats/")
async def rebuild_folder_statistics(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Rebuild all folder statistics and metadata"""
    
    try:
        # Verify collection exists
        collection = await db.execute(
            select(KBCollection).where(KBCollection.id == collection_id)
        )
        if not collection.scalar_one_or_none():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Collection {collection_id} not found"
            )
        
        # Rebuild statistics
        await FolderHierarchyService.update_folder_statistics(collection_id, db)
        
        return {
            "message": "Folder statistics rebuilt successfully",
            "collection_id": collection_id
        }
        
    except Exception as e:
        logger.error(f"Failed to rebuild folder statistics: {e}")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild folder statistics: {str(e)}"
        )


# Helper functions

def _filter_folder_tree(folder_tree: List[dict], folder_type: str = None, max_depth: int = None) -> List[dict]:
    """Apply filters to folder tree recursively"""
    filtered_tree = []
    
    for folder in folder_tree:
        # Check depth filter
        if max_depth is not None and folder.get("depth", 0) > max_depth:
            continue
        
        # Check folder type filter
        if folder_type:
            folder_metadata = folder.get("folder_metadata", {})
            if folder_metadata.get("folder_type") != folder_type:
                continue
        
        # Recursively filter children
        if "children" in folder:
            folder["children"] = _filter_folder_tree(
                folder["children"], 
                folder_type=folder_type, 
                max_depth=max_depth
            )
        
        filtered_tree.append(folder)
    
    return filtered_tree


def _count_folders_in_tree(folder_tree: List[dict]) -> int:
    """Count total folders in tree structure"""
    total = len(folder_tree)
    
    for folder in folder_tree:
        if "children" in folder:
            total += _count_folders_in_tree(folder["children"])
    
    return total