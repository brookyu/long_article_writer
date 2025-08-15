#!/usr/bin/env python3
"""
Simple test to verify the embedding test endpoint works
"""

import asyncio
import aiohttp
import json

async def test_embedding_endpoint():
    """Test the embedding endpoint directly"""
    url = "http://localhost:8000/api/settings/test-embedding"
    data = {
        "provider": "ollama",
        "model": "nomic-embed-text",
        "base_url": "http://localhost:11434"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                text = await response.text()
                print(f"Response: {text}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"Success: {result}")
                else:
                    print(f"Error: {text}")
                    
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_embedding_endpoint())