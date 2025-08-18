"""
Settings model for storing provider configurations
"""

from sqlalchemy import Column, String, Text, Boolean, JSON
from .base import BaseModel


class Setting(BaseModel):
    """Settings for LLM providers, embedding models, etc."""
    __tablename__ = "settings"
    
    provider = Column(String(50), nullable=False, comment="Provider type: ollama, openai, anthropic, serpapi, language, etc.")
    key_alias = Column(String(100), nullable=False, comment="Human-readable name for this configuration")
    encrypted_secret = Column(Text, comment="Encrypted API key or secret")
    model_name = Column(String(100), comment="Specific model name to use")
    config_json = Column(JSON, comment="Additional provider-specific configuration")
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether this configuration is currently active")
    
    def __repr__(self):
        return f"<Setting(provider='{self.provider}', key_alias='{self.key_alias}', active={self.is_active})>"