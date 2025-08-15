"""
Minimal FastAPI backend for testing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(
    title="Long Article Writer API",
    description="AI-powered long-form article generation with knowledge base integration",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Long Article Writer API",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "long-article-writer-backend",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "long-article-writer-backend",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/settings")
async def get_settings():
    return [
        {
            "id": 1,
            "provider": "ollama",
            "key_alias": "Local Mixtral",
            "model_name": "mixtral:latest",
            "is_active": True
        },
        {
            "id": 2,
            "provider": "ollama", 
            "key_alias": "Local Embedding",
            "model_name": "nomic-embed-text",
            "is_active": True
        }
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)