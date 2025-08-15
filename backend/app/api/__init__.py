"""
API routes module
"""

from fastapi import APIRouter

from app.api.routes import health, settings, collections, articles

# Create main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(collections.router, prefix="/kb/collections", tags=["collections"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])