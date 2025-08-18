"""
Folder hierarchy models for organizing knowledge base documents
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseModel


class FolderNode(BaseModel):
    """Represents a folder node in the hierarchical structure"""
    __tablename__ = "folder_nodes"
    
    collection_id = Column(Integer, ForeignKey("kb_collections.id"), nullable=False)
    upload_job_id = Column(Integer, ForeignKey("upload_jobs.id"), nullable=True)
    
    # Hierarchy structure
    name = Column(String(255), nullable=False, comment="Folder name")
    full_path = Column(String(1000), nullable=False, comment="Complete path from root")
    parent_id = Column(Integer, ForeignKey("folder_nodes.id"), nullable=True, comment="Parent folder")
    depth = Column(Integer, default=0, comment="Depth level in hierarchy")
    
    # Content statistics
    document_count = Column(Integer, default=0, comment="Number of documents in this folder")
    total_documents = Column(Integer, default=0, comment="Total documents including subfolders")
    total_size_bytes = Column(Integer, default=0, comment="Total size of all documents")
    
    # Metadata
    folder_metadata = Column(JSON, comment="Additional folder metadata")
    auto_tags = Column(JSON, comment="Auto-generated tags based on content")
    content_summary = Column(Text, comment="AI-generated summary of folder contents")
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    collection = relationship("KBCollection", back_populates="folder_nodes")
    upload_job = relationship("UploadJob")
    parent = relationship("FolderNode", remote_side="FolderNode.id", back_populates="children")
    children = relationship("FolderNode", back_populates="parent", cascade="all, delete-orphan")
    # documents relationship will be handled via queries rather than direct relationship
    # documents = relationship("KBDocument", viewonly=True)
    
    def to_dict(self, include_children: bool = False, include_documents: bool = False) -> Dict[str, Any]:
        """Convert folder node to dictionary"""
        result = {
            "id": self.id,
            "name": self.name,
            "full_path": self.full_path,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "document_count": self.document_count,
            "total_documents": self.total_documents,
            "total_size_bytes": self.total_size_bytes,
            "folder_metadata": self.folder_metadata or {},
            "auto_tags": self.auto_tags or [],
            "content_summary": self.content_summary,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if include_children and self.children:
            result["children"] = [child.to_dict(include_children=True) for child in self.children]
        
        # Documents will be loaded separately via queries when needed
        if include_documents:
            result["documents"] = []  # Will be populated by service methods
        
        return result
    
    def get_hierarchy_path(self) -> List[str]:
        """Get the full hierarchy path as a list of folder names"""
        if not self.full_path:
            return []
        return [part for part in self.full_path.split('/') if part]
    
    def get_breadcrumb(self) -> List[Dict[str, Any]]:
        """Get breadcrumb navigation for this folder"""
        path_parts = self.get_hierarchy_path()
        breadcrumb = []
        
        current_path = ""
        for i, part in enumerate(path_parts):
            current_path = f"{current_path}/{part}" if current_path else part
            breadcrumb.append({
                "name": part,
                "path": current_path,
                "depth": i,
                "is_current": i == len(path_parts) - 1
            })
        
        return breadcrumb


class FolderHierarchyService:
    """Service for managing folder hierarchy operations"""
    
    @staticmethod
    async def create_folder_structure(
        collection_id: int,
        folder_paths: List[str],
        upload_job_id: Optional[int] = None,
        db = None
    ) -> List[FolderNode]:
        """Create folder structure from a list of paths"""
        from sqlalchemy import select
        
        created_folders = []
        folder_cache = {}  # path -> folder_node
        
        # Sort paths to ensure parent folders are created first
        sorted_paths = sorted(set(folder_paths))
        
        for path in sorted_paths:
            if not path or path in folder_cache:
                continue
            
            path_parts = [part for part in path.split('/') if part]
            if not path_parts:
                continue
            
            # Build path incrementally to ensure all parent folders exist
            current_path = ""
            parent_id = None
            
            for i, part in enumerate(path_parts):
                current_path = f"{current_path}/{part}" if current_path else part
                depth = i
                
                if current_path in folder_cache:
                    parent_id = folder_cache[current_path].id
                    continue
                
                # Check if folder already exists
                existing = await db.execute(
                    select(FolderNode).where(
                        FolderNode.collection_id == collection_id,
                        FolderNode.full_path == current_path
                    )
                )
                existing_folder = existing.scalar_one_or_none()
                
                if existing_folder:
                    folder_cache[current_path] = existing_folder
                    parent_id = existing_folder.id
                else:
                    # Create new folder
                    new_folder = FolderNode(
                        collection_id=collection_id,
                        upload_job_id=upload_job_id,
                        name=part,
                        full_path=current_path,
                        parent_id=parent_id,
                        depth=depth
                    )
                    
                    db.add(new_folder)
                    await db.flush()  # Get the ID
                    
                    folder_cache[current_path] = new_folder
                    created_folders.append(new_folder)
                    parent_id = new_folder.id
        
        await db.commit()
        return created_folders
    
    @staticmethod
    async def update_folder_statistics(
        collection_id: int,
        db = None
    ):
        """Update document counts and size statistics for all folders"""
        from sqlalchemy import select, func, update
        
        # Get all folders for the collection
        folders_result = await db.execute(
            select(FolderNode)
            .where(FolderNode.collection_id == collection_id)
            .order_by(FolderNode.depth.desc())  # Start from deepest folders
        )
        folders = folders_result.scalars().all()
        
        for folder in folders:
            # Count direct documents in this folder
            direct_docs = await db.execute(
                select(func.count(), func.sum(KBDocument.size_bytes))
                .select_from(KBDocument)
                .where(
                    KBDocument.collection_id == collection_id,
                    KBDocument.folder_path == folder.full_path
                )
            )
            direct_count, direct_size = direct_docs.one()
            direct_count = direct_count or 0
            direct_size = direct_size or 0
            
            # Count documents in all subfolders
            subfolder_docs = await db.execute(
                select(func.count(), func.sum(KBDocument.size_bytes))
                .select_from(KBDocument)
                .where(
                    KBDocument.collection_id == collection_id,
                    KBDocument.folder_path.like(f"{folder.full_path}/%")
                )
            )
            subfolder_count, subfolder_size = subfolder_docs.one()
            subfolder_count = subfolder_count or 0
            subfolder_size = subfolder_size or 0
            
            total_count = direct_count + subfolder_count
            total_size = direct_size + subfolder_size
            
            # Update folder statistics
            await db.execute(
                update(FolderNode)
                .where(FolderNode.id == folder.id)
                .values(
                    document_count=direct_count,
                    total_documents=total_count,
                    total_size_bytes=total_size,
                    last_updated=func.now()
                )
            )
        
        await db.commit()
    
    @staticmethod
    async def get_folder_tree(
        collection_id: int,
        include_documents: bool = False,
        db = None
    ) -> List[Dict[str, Any]]:
        """Get the complete folder tree structure"""
        from sqlalchemy import select
        
        # Get all folders
        folders_result = await db.execute(
            select(FolderNode)
            .where(FolderNode.collection_id == collection_id)
            .order_by(FolderNode.depth, FolderNode.name)
        )
        folders = folders_result.scalars().all()
        
        # Build tree structure
        folder_dict = {folder.id: folder.to_dict(include_documents=include_documents) for folder in folders}
        root_folders = []
        
        for folder in folders:
            folder_data = folder_dict[folder.id]
            if folder.parent_id and folder.parent_id in folder_dict:
                parent_data = folder_dict[folder.parent_id]
                if "children" not in parent_data:
                    parent_data["children"] = []
                parent_data["children"].append(folder_data)
            else:
                root_folders.append(folder_data)
        
        return root_folders
    
    @staticmethod
    def generate_auto_tags(folder_path: str, document_count: int) -> List[str]:
        """Generate automatic tags based on folder structure and content"""
        tags = []
        
        path_parts = [part.lower() for part in folder_path.split('/') if part]
        
        # Add path-based tags
        for part in path_parts:
            # Clean up folder names for tags
            clean_part = part.replace('_', ' ').replace('-', ' ')
            if len(clean_part) > 2:
                tags.append(clean_part)
        
        # Add depth-based tags
        depth = len(path_parts)
        if depth == 1:
            tags.append("top-level")
        elif depth > 3:
            tags.append("deep-nested")
        
        # Add content-based tags
        if document_count > 10:
            tags.append("large-collection")
        elif document_count > 0:
            tags.append("small-collection")
        else:
            tags.append("empty-folder")
        
        # Common folder type detection
        folder_types = {
            'docs': ['documentation', 'reference'],
            'documentation': ['documentation', 'reference'],
            'api': ['api', 'technical'],
            'guide': ['tutorial', 'guide'],
            'tutorial': ['tutorial', 'guide'],
            'example': ['example', 'sample'],
            'test': ['testing', 'quality-assurance'],
            'config': ['configuration', 'settings'],
            'src': ['source-code', 'development'],
            'lib': ['library', 'utility'],
            'util': ['utility', 'helper'],
            'data': ['data', 'dataset'],
            'image': ['media', 'visual'],
            'asset': ['media', 'resource']
        }
        
        for part in path_parts:
            if part in folder_types:
                tags.extend(folder_types[part])
        
        return list(set(tags))  # Remove duplicates


# Note: The relationship to KBCollection will be added in __init__.py to avoid circular imports