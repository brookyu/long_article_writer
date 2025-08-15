"""
Web search integration for knowledge augmentation
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import httpx
from urllib.parse import quote_plus, urljoin, urlparse
from bs4 import BeautifulSoup
import hashlib

logger = logging.getLogger(__name__)


class WebSearchResult:
    """Represents a web search result with extracted content"""
    
    def __init__(self, title: str, url: str, snippet: str, content: str = "", relevance_score: float = 0.0):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.content = content
        self.relevance_score = relevance_score
        self.extracted_at = datetime.now()
        self.hash = hashlib.md5(f"{url}_{title}".encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "relevance_score": self.relevance_score,
            "extracted_at": self.extracted_at.isoformat(),
            "source_type": "web_search",
            "hash": self.hash
        }


class WebContentExtractor:
    """Extracts clean content from web pages"""
    
    def __init__(self):
        self.timeout = 30
        self.max_content_length = 10000  # Limit content size
    
    async def extract_content(self, url: str) -> str:
        """Extract main content from a web page"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                    element.decompose()
                
                # Try to find main content
                content_selectors = [
                    'article', 'main', '[role="main"]', 
                    '.content', '.post-content', '.entry-content',
                    '.article-body', '.story-body'
                ]
                
                content = ""
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        content = elements[0].get_text(strip=True)
                        break
                
                # Fallback to body content
                if not content:
                    body = soup.find('body')
                    if body:
                        content = body.get_text(strip=True)
                
                # Clean and limit content
                content = re.sub(r'\s+', ' ', content)
                content = content[:self.max_content_length]
                
                return content
                
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return ""


class DuckDuckGoSearchProvider:
    """DuckDuckGo search provider (no API key required)"""
    
    def __init__(self):
        self.base_url = "https://html.duckduckgo.com/html/"  # Use the redirect URL directly
        self.extractor = WebContentExtractor()
    
    async def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """Search using DuckDuckGo"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            params = {
                "q": query,
                "s": "0",  # Start from first result
                "dc": str(max_results * 2)  # Request more to filter
            }
            
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(self.base_url, params=params, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # Parse DuckDuckGo results
                result_elements = soup.find_all('div', class_='result')
                
                for element in result_elements[:max_results]:
                    try:
                        # Extract title and URL
                        title_elem = element.find('a', class_='result__a')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                        
                        # Extract snippet
                        snippet_elem = element.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        # Skip if we don't have essential info
                        if not title or not url:
                            continue
                        
                        # Create result
                        result = WebSearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            relevance_score=1.0 - (len(results) * 0.1)  # Simple ranking
                        )
                        
                        results.append(result)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse search result: {e}")
                        continue
                
                # Extract content for top results
                for result in results[:3]:  # Only extract content for top 3
                    content = await self.extractor.extract_content(result.url)
                    result.content = content
                
                logger.info(f"DuckDuckGo search found {len(results)} results for: {query}")
                return results
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []


class SerperGoogleSearchProvider:
    """Google Search via Serper API (requires API key)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev/search"
        self.extractor = WebContentExtractor()
    
    async def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """Search using Google via Serper API"""
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query,
                "num": max_results
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                # Parse organic results
                organic_results = data.get("organic", [])
                
                for i, item in enumerate(organic_results[:max_results]):
                    try:
                        title = item.get("title", "")
                        url = item.get("link", "")
                        snippet = item.get("snippet", "")
                        
                        if not title or not url:
                            continue
                        
                        result = WebSearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            relevance_score=1.0 - (i * 0.1)
                        )
                        
                        results.append(result)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse Google result: {e}")
                        continue
                
                # Extract content for top results
                for result in results[:3]:
                    content = await self.extractor.extract_content(result.url)
                    result.content = content
                
                logger.info(f"Google search found {len(results)} results for: {query}")
                return results
                
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []


class WebSearchManager:
    """Manages multiple web search providers"""
    
    def __init__(self):
        self.providers = {}
        self.default_provider = "duckduckgo"
        
        # Initialize DuckDuckGo (no API key required)
        self.providers["duckduckgo"] = DuckDuckGoSearchProvider()
    
    def add_google_provider(self, api_key: str):
        """Add Google search provider with API key"""
        self.providers["google"] = SerperGoogleSearchProvider(api_key)
    
    async def search(
        self,
        query: str,
        provider: str = None,
        max_results: int = 5,
        extract_content: bool = True
    ) -> List[WebSearchResult]:
        """Search using specified or default provider"""
        
        provider_name = provider or self.default_provider
        
        if provider_name not in self.providers:
            logger.error(f"Unknown search provider: {provider_name}")
            return []
        
        search_provider = self.providers[provider_name]
        
        try:
            logger.info(f"Searching '{query}' using {provider_name}")
            results = await search_provider.search(query, max_results)
            
            logger.info(f"Found {len(results)} web search results")
            return results
            
        except Exception as e:
            logger.error(f"Web search failed with {provider_name}: {e}")
            return []
    
    def get_available_providers(self) -> List[str]:
        """Get list of available search providers"""
        return list(self.providers.keys())


class HybridResearchEngine:
    """Combines local knowledge base search with web search"""
    
    def __init__(self, local_search_function, web_search_manager: WebSearchManager):
        self.local_search = local_search_function
        self.web_search = web_search_manager
        self.confidence_threshold = 0.7  # Configurable threshold
        self.max_local_results = 5
        self.max_web_results = 3
    
    async def research_topic(
        self,
        collection_id: int,
        query: str,
        use_web_search: bool = True,
        confidence_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Research a topic using both local KB and web search
        
        Returns:
            Dict with local and web results, plus metadata about sources
        """
        
        threshold = confidence_threshold or self.confidence_threshold
        
        research_results = {
            "query": query,
            "local_results": [],
            "web_results": [],
            "total_sources": 0,
            "source_breakdown": {
                "local": 0,
                "web": 0
            },
            "confidence_score": 0.0,
            "search_strategy": "local_only",
            "generated_at": datetime.now().isoformat()
        }
        
        # Step 1: Search local knowledge base
        logger.info(f"Searching local knowledge base for: {query}")
        try:
            local_response = await self.local_search(collection_id, query)
            local_results = local_response.get("matches", [])
            
            # Calculate confidence based on relevance scores
            if local_results:
                avg_relevance = sum(r.get("relevance_score", 0) for r in local_results) / len(local_results)
                research_results["confidence_score"] = avg_relevance
                research_results["local_results"] = local_results[:self.max_local_results]
                research_results["source_breakdown"]["local"] = len(research_results["local_results"])
            
            logger.info(f"Local search: {len(local_results)} results, confidence: {research_results['confidence_score']:.2f}")
            
        except Exception as e:
            logger.error(f"Local search failed: {e}")
        
        # Step 2: Decide if web search is needed
        needs_web_search = (
            use_web_search and 
            research_results["confidence_score"] < threshold
        )
        
        if needs_web_search:
            research_results["search_strategy"] = "hybrid"
            logger.info(f"Confidence {research_results['confidence_score']:.2f} < {threshold}, performing web search")
            
            try:
                web_results = await self.web_search.search(query, max_results=self.max_web_results)
                
                # Convert web results to compatible format
                formatted_web_results = []
                for result in web_results:
                    formatted_result = {
                        "title": result.title,
                        "url": result.url,
                        "preview": result.snippet,
                        "content": result.content,
                        "relevance_score": result.relevance_score,
                        "source_type": "web_search",
                        "char_count": len(result.content)
                    }
                    formatted_web_results.append(formatted_result)
                
                research_results["web_results"] = formatted_web_results
                research_results["source_breakdown"]["web"] = len(formatted_web_results)
                
                logger.info(f"Web search: {len(formatted_web_results)} results added")
                
            except Exception as e:
                logger.error(f"Web search failed: {e}")
        
        else:
            research_results["search_strategy"] = "local_only"
            logger.info("Local confidence sufficient, skipping web search")
        
        research_results["total_sources"] = (
            research_results["source_breakdown"]["local"] + 
            research_results["source_breakdown"]["web"]
        )
        
        return research_results
    
    def set_confidence_threshold(self, threshold: float):
        """Update the confidence threshold for triggering web search"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Updated confidence threshold to {self.confidence_threshold}")


# Global instances
web_search_manager = WebSearchManager()
# hybrid_research_engine will be initialized with local search function