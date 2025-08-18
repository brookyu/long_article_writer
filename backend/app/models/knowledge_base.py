"""
Knowledge base models for collections, documents, and chunks
"""

from sqlalchemy import Column, String, Text, Integer, BigInteger, Boolean, ForeignKey, Enum, JSON, Computed
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class DocumentStatus(str, enum.Enum):
    """Document processing status"""
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class KBCollection(BaseModel):
    """Knowledge base collections for document organization"""
    __tablename__ = "kb_collections"
    
    name = Column(String(255), nullable=False, unique=True, comment="Collection name")
    description = Column(Text, comment="Collection description")
    embedding_model = Column(String(100), comment="Model used for embeddings in this collection")
    total_documents = Column(Integer, default=0, comment="Number of documents in collection")
    total_chunks = Column(Integer, default=0, comment="Number of chunks in collection")
    
    # Relationships
    documents = relationship("KBDocument", back_populates="collection", cascade="all, delete-orphan")
    articles = relationship("Article", back_populates="collection", cascade="all, delete-orphan")
    upload_jobs = relationship("UploadJob", back_populates="collection", cascade="all, delete-orphan")
    folder_nodes = relationship("FolderNode", back_populates="collection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<KBCollection(name='{self.name}', documents={self.total_documents})>"


class KBDocument(BaseModel):
    """Document metadata and status tracking"""
    __tablename__ = "kb_documents"
    
    collection_id = Column(Integer, ForeignKey("kb_collections.id"), nullable=False, comment="Parent collection")
    filename = Column(String(255), nullable=False, comment="Display filename")
    original_filename = Column(String(255), nullable=False, comment="Original uploaded filename")
    mime_type = Column(String(100), comment="File MIME type")
    size_bytes = Column(BigInteger, comment="File size in bytes")
    sha256 = Column(String(64), nullable=False, comment="File hash for deduplication")
    file_path = Column(String(500), comment="Local storage path")
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False, comment="Processing status")
    error_message = Column(Text, comment="Error details if processing failed")
    chunk_count = Column(Integer, default=0, comment="Number of chunks created")
    
    # Folder structure support
    relative_path = Column(String(500), comment="Path within uploaded folder structure")
    parent_folder = Column(String(255), comment="Parent folder name")
    folder_depth = Column(Integer, default=0, comment="Depth level in folder hierarchy")
    folder_path = Column(String(1000), comment="Full folder path from root")
    upload_job_id = Column(Integer, ForeignKey("upload_jobs.id"), nullable=True, comment="Associated upload job")
    
    # Hierarchical metadata
    folder_metadata = Column(JSON, comment="Folder structure and metadata")
    document_tags = Column(JSON, comment="Auto-generated tags based on folder location")
    content_category = Column(String(100), comment="Category inferred from folder structure")
    
    # Relationships
    collection = relationship("KBCollection", back_populates="documents")
    chunks = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<KBDocument(filename='{self.filename}', status='{self.status}')>"


class KBChunk(BaseModel):
    """Document chunks for reference and debugging"""
    __tablename__ = "kb_chunks"
    
    document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=False, comment="Parent document")
    chunk_index = Column(Integer, nullable=False, comment="Order within the document")
    text = Column(Text, nullable=False, comment="Chunk text content")
    char_count = Column(Integer, Computed("char_length(text)"), comment="Character count of chunk")
    milvus_id = Column(String(100), comment="Reference to Milvus vector ID")
    
    # Relationships
    document = relationship("KBDocument", back_populates="chunks")
    
    def __repr__(self):
        return f"<KBChunk(document_id={self.document_id}, index={self.chunk_index})>"


class ArticleStatus(str, enum.Enum):
    """Article generation status - matching existing DB schema"""
    OUTLINING = "outlining"
    DRAFTING = "drafting"
    REFINING = "refining"
    COMPLETED = "completed"
    EXPORTED = "exported"


class Article(BaseModel):
    """Generated article model - matching existing articles table"""
    __tablename__ = "articles"
    
    # Basic info (matching existing schema)
    title = Column(String(255), comment="Article title")
    topic = Column(String(255), nullable=False, comment="Article topic")
    collection_id = Column(Integer, ForeignKey("kb_collections.id"), comment="Primary knowledge base used")
    
    # Content and structure
    outline_json = Column(Text, comment="Generated outline structure as JSON")  # Using Text instead of JSON for SQLite compatibility
    content_markdown = Column(Text, comment="Current article content")
    markdown_path = Column(String(500), comment="Path to exported markdown file")
    
    # Status and metrics
    status = Column(Enum(ArticleStatus), default=ArticleStatus.OUTLINING, nullable=False)
    word_count = Column(Integer, default=0, comment="Word count of the article")
    source_count = Column(Integer, default=0, comment="Number of sources cited")
    local_source_ratio = Column(Integer, default=0, comment="Ratio of local vs web sources (as percentage)")
    
    # Additional metadata for our enhanced system
    generation_time_seconds = Column(Integer, comment="Time taken to generate in seconds")
    writing_style = Column(String(100), default="professional", comment="Writing style used")
    article_type = Column(String(100), default="comprehensive", comment="Article type")
    target_length = Column(String(50), default="medium", comment="Target length (short/medium/long)")
    model_used = Column(String(100), comment="LLM model used for generation")
    
    # Collection relationship
    collection = relationship("KBCollection", back_populates="articles")
    
    def __repr__(self):
        return f"<Article(title='{self.title}', status='{self.status}')>"