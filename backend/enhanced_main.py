"""
Enhanced FastAPI backend with database integration
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Import our database and models
from app.core.database import init_db
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management"""
    print("🚀 Starting Long Article Writer API...")
    
    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    print("🛑 Shutting down Long Article Writer API...")


app = FastAPI(
    title="Long Article Writer API",
    description="AI-powered long-form article generation with knowledge base integration",
    version="0.1.0",
    lifespan=lifespan
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

# Import and include API routes
from app.api import api_router
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "enhanced_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )