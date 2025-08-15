"""
Ollama client for embeddings and text generation
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Custom exception for Ollama-related errors"""
    pass


class OllamaClient:
    """Async client for Ollama API"""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}"
        self.timeout = 300  # 5 minutes for large embeddings
        
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make an async request to Ollama"""
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=data)
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
            response = await self._make_request("api/tags", {})
            models = response.get("models", [])
            available_models = [model["name"] for model in models]
            return model_name in available_models or f"{model_name}:latest" in available_models
        except Exception as e:
            logger.warning(f"Could not check model availability: {e}")
            return False
    
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
    
    async def generate_text(self, prompt: str, model: str = "mixtral:latest", max_tokens: int = 1000) -> str:
        """Generate text using Ollama"""
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Ensure model name includes tag
        if ":" not in model:
            model = f"{model}:latest"
        
        # Check if model is available
        # Temporarily bypass model check for debugging
        # if not await self.check_model_availability(model):
        #     raise OllamaError(f"Text generation model '{model}' not available")
        
        try:
            logger.debug(f"Generating text with model {model}")
            
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            }
            
            response = await self._make_request("api/generate", data)
            
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