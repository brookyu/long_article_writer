"""
Long Article Writer - FastAPI Backend
Main application entry point
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import get_settings
from app.core.database import init_db
from app.api import api_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management"""
    settings = get_settings()
    
    # Initialize Sentry if DSN is provided
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(auto_enabling_integrations=False),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=1.0,
            environment=settings.ENVIRONMENT,
        )
        logger.info("Sentry initialized", dsn_configured=True)
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Application shutdown")


# Create FastAPI application
app = FastAPI(
    title="Long Article Writer API",
    description="AI-powered long-form article generation with knowledge base integration",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3005",  # Frontend dev server
        "http://frontend:3000",
        "http://frontend:3005"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with logging"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again.",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    return {
        "status": "healthy",
        "service": "long-article-writer-backend",
        "version": "0.1.0"
    }


# Include API routes
app.include_router(api_router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Long Article Writer API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )