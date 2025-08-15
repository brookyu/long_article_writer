"""
Configuration management using Pydantic Settings
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./long_article_writer.db",
        description="Database URL (SQLite for development, MySQL for production)"
    )
    
    # Milvus Vector Database
    MILVUS_HOST: str = Field(default="localhost", description="Milvus host")
    MILVUS_PORT: int = Field(default=19530, description="Milvus port")
    MILVUS_COLLECTION_PREFIX: str = Field(default="law_", description="Milvus collection prefix")
    
    # Ollama Configuration
    OLLAMA_HOST: str = Field(default="localhost", description="Ollama host")
    OLLAMA_PORT: int = Field(default=11434, description="Ollama port")
    OLLAMA_BASE_URL: Optional[str] = Field(default=None, description="Full Ollama base URL")
    
    # Default Models
    DEFAULT_LLM_MODEL: str = Field(default="llama3.1:8b", description="Default LLM model")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="nomic-embed-text", description="Default embedding model")
    
    # File Storage
    UPLOAD_DIR: str = Field(default="uploads", description="Upload directory")
    EXPORT_DIR: str = Field(default="exports", description="Export directory")
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, description="Max file size in bytes (100MB)")
    
    # Document Processing
    CHUNK_SIZE: int = Field(default=1000, description="Default chunk size for documents")
    CHUNK_OVERLAP: int = Field(default=200, description="Chunk overlap size")
    
    # Retrieval Configuration
    DEFAULT_TOP_K: int = Field(default=5, description="Default number of chunks to retrieve")
    CONFIDENCE_THRESHOLD: float = Field(default=0.7, description="Minimum confidence for local retrieval")
    
    # Web Search (optional)
    SERPAPI_KEY: Optional[str] = Field(default=None, description="SerpAPI key for web search")
    TAVILY_API_KEY: Optional[str] = Field(default=None, description="Tavily API key for web search")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for encryption"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def ollama_url(self) -> str:
        """Get complete Ollama URL"""
        if self.OLLAMA_BASE_URL:
            return self.OLLAMA_BASE_URL
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"
    
    @property
    def upload_path(self) -> str:
        """Get absolute upload path"""
        if os.path.isabs(self.UPLOAD_DIR):
            return self.UPLOAD_DIR
        return os.path.join(os.getcwd(), self.UPLOAD_DIR)
    
    @property
    def export_path(self) -> str:
        """Get absolute export path"""
        if os.path.isabs(self.EXPORT_DIR):
            return self.EXPORT_DIR
        return os.path.join(os.getcwd(), self.EXPORT_DIR)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()