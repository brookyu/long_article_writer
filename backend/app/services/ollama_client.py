"""
Ollama client for embeddings and text generation
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
import httpx
from app.core.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Custom exception for Ollama-related errors"""
    pass


class OllamaClient:
    """Async client for Ollama API"""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}"
        self.default_timeout = 300  # 5 minutes for embeddings
        self.generation_timeout = 600  # 10 minutes for large model text generation
        self.refinement_timeout = 180  # 3 minutes for refinement tasks (shorter for better UX)
        
    async def _make_request(self, endpoint: str, data: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, method: str = "POST") -> Dict[str, Any]:
        """Make an async request to Ollama"""
        url = f"{self.base_url}/{endpoint}"
        request_timeout = timeout or self.default_timeout
        
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(url, json=data or {})
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                raise OllamaError(f"Ollama request timed out: {endpoint}")
            except httpx.HTTPStatusError as e:
                raise OllamaError(f"Ollama HTTP error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise OllamaError(f"Ollama request failed: {str(e)}")
    
    async def check_model_availability(self, model_name: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            response = await self._make_request("api/tags", method="GET")
            models = response.get("models", [])
            available_models = [model["name"] for model in models]
            return model_name in available_models or f"{model_name}:latest" in available_models
        except Exception as e:
            logger.warning(f"Could not check model availability: {e}")
            return False
    
    async def get_user_llm_model(self, db: Optional[AsyncSession] = None) -> str:
        """Get the user's selected LLM model from settings"""
        if not db:
            # If no DB session provided, return a good default
            return await self._get_best_available_model()
            
        try:
            # Import here to avoid circular imports
            from app.models.settings import Setting
            
            # Get LLM settings from database
            result = await db.execute(
                select(Setting).where(Setting.key_alias.ilike('%llm%'))
            )
            llm_setting = result.scalar_one_or_none()
            
            if llm_setting:
                # Check model_name field first
                if llm_setting.model_name:
                    logger.info(f"Using user-selected model from model_name: {llm_setting.model_name}")
                    return llm_setting.model_name
                # Check config_json for model field
                elif llm_setting.config_json and llm_setting.config_json.get('model'):
                    model = llm_setting.config_json['model']
                    logger.info(f"Using user-selected model from config: {model}")
                    return model
            else:
                # No user setting found, get best available model
                return await self._get_best_available_model()
                
        except Exception as e:
            logger.error(f"Failed to get user LLM model: {e}")
            return await self._get_best_available_model()
    
    async def get_user_embedding_model(self, db: Optional[AsyncSession] = None) -> str:
        """Get user's configured embedding model or default"""
        if not db:
            # If no DB session provided, return default
            return "nomic-embed-text"
            
        try:
            # Import here to avoid circular imports
            from app.models.settings import Setting
            
            # Get embedding settings from database
            result = await db.execute(
                select(Setting).where(Setting.key_alias.ilike('%embed%'))
            )
            embedding_setting = result.scalar_one_or_none()
            
            if embedding_setting:
                # Check model_name field first
                if embedding_setting.model_name:
                    logger.info(f"Using user-selected embedding model from model_name: {embedding_setting.model_name}")
                    return embedding_setting.model_name
                # Check config_json for model field
                elif embedding_setting.config_json and embedding_setting.config_json.get('model'):
                    model = embedding_setting.config_json['model']
                    logger.info(f"Using user-selected embedding model from config: {model}")
                    return model
            
            # No user setting found, return default
            logger.info("No user embedding setting found, using default: nomic-embed-text")
            return "nomic-embed-text"
                
        except Exception as e:
            logger.error(f"Failed to get user embedding model: {e}")
            return "nomic-embed-text"
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available Ollama models"""
        try:
            response = await self._make_request("api/tags", method="GET")
            models = response.get("models", [])
            
            # Extract model names and details
            model_list = []
            for model in models:
                model_info = {
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                    "parameter_size": model.get("details", {}).get("parameter_size", ""),
                    "family": model.get("details", {}).get("family", "")
                }
                model_list.append(model_info)
            
            # Sort by modified_at (most recent first)
            model_list.sort(key=lambda x: x["modified_at"], reverse=True)
            return model_list
            
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            # Return some default models as fallback
            return [
                {"name": "gpt-oss:20b", "size": 0, "modified_at": "", "parameter_size": "20.9B", "family": "gptoss"},
                {"name": "nomic-embed-text:latest", "size": 0, "modified_at": "", "parameter_size": "137M", "family": "nomic-bert"}
            ]

    async def _get_best_available_model(self) -> str:
        """Get the best available model for local development"""
        try:
            # Preferred models in order (smallest/fastest first)
            preferred_models = [
                "llama3.2:1b",      # Fastest option
                "llama3.2:3b",      # Very fast, good quality
                "phi3:mini",        # Microsoft's small model
                "gemma2:2b",        # Google's small model
                "qwen2.5:7b",       # Good alternative
                "gpt-oss:20b",      # Slower fallback
                "mixtral:latest"    # Largest fallback (avoid if possible)
            ]
            
            for model in preferred_models:
                if await self.check_model_availability(model):
                    logger.info(f"Selected best available model: {model}")
                    return model
            
            # If none available, return a common default
            logger.warning("No preferred models available, using default")
            return "llama3.2:3b"
            
        except Exception as e:
            logger.error(f"Failed to get best available model: {e}")
            return "llama3.2:3b"
    
    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        """Generate embedding for text using Ollama"""
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Ensure model name includes tag
        if ":" not in model:
            model = f"{model}:latest"
        
        # Check if model is available
        if not await self.check_model_availability(model):
            raise OllamaError(f"Embedding model '{model}' not available")
        
        try:
            logger.debug(f"Generating embedding for text of length {len(text)}")
            
            data = {
                "model": model,
                "prompt": text,
            }
            
            response = await self._make_request("api/embeddings", data)
            
            embedding = response.get("embedding")
            if not embedding:
                raise OllamaError("No embedding returned from Ollama")
            
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        embeddings = []
        for i, text in enumerate(texts):
            try:
                embedding = await self.generate_embedding(text, model)
                embeddings.append(embedding)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Generated {i + 1}/{len(texts)} embeddings")
                    
            except Exception as e:
                logger.error(f"Failed to generate embedding for text {i}: {e}")
                # Add empty embedding as placeholder
                embeddings.append([])
        
        logger.info(f"Completed embedding generation: {len([e for e in embeddings if e])} successful")
        return embeddings
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, max_tokens: int = 1000, db: Optional[AsyncSession] = None, is_refinement: bool = False) -> str:
        """Generate text using Ollama"""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Get user's selected model if none provided
        if not model:
            model = await self.get_user_llm_model(db)
        
        # Ensure model name includes tag
        if ":" not in model:
            model = f"{model}:latest"
        
        # Check if model is available
        # Temporarily bypass model check for debugging
        # if not await self.check_model_availability(model):
        #     raise OllamaError(f"Text generation model '{model}' not available")
        
        try:
            logger.info(f"🤖 Generating text with model: {model}")
            logger.debug(f"Generating text with model {model}")
            
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_thread": 4,  # Optimize for M4 processor
                    "repeat_penalty": 1.1,
                    "top_k": 40,
                    "num_ctx": 4096,  # Reasonable context window
                }
            }
            
            # Use shorter timeout for refinement tasks
            timeout = self.refinement_timeout if is_refinement else self.generation_timeout
            response = await self._make_request("api/generate", data, timeout=timeout)
            
            generated_text = response.get("response", "").strip()
            if not generated_text:
                raise OllamaError("No text generated")
            
            logger.debug(f"Generated {len(generated_text)} characters")
            return generated_text
            
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Generate a summary of the text"""
        prompt = f"""Please provide a concise summary of the following text in no more than {max_length} words:

{text}

Summary:"""
        
        try:
            summary = await self.generate_text(prompt, max_tokens=max_length * 2)
            return summary
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            return "Summary not available"
    
    async def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        prompt = f"""Extract the {max_keywords} most important keywords from the following text. Return only the keywords, separated by commas:

{text}

Keywords:"""
        
        try:
            response = await self.generate_text(prompt, max_tokens=100)
            keywords = [kw.strip() for kw in response.split(",") if kw.strip()]
            return keywords[:max_keywords]
        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            return []


# Global client instance
ollama_client = OllamaClient()