"""
API routes module
"""

from fastapi import APIRouter

from app.api.routes import health, settings, collections, articles, enhanced_agents, folder_upload, folder_hierarchy, simple_upload
# Note: chat routes temporarily disabled due to dependency conflicts
# from app.api.routes import chat

# Create main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(collections.router, prefix="/kb/collections", tags=["collections"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(enhanced_agents.router, prefix="/enhanced-agents", tags=["enhanced-agents"])
api_router.include_router(folder_upload.router, prefix="/kb/collections", tags=["folder-upload"])
api_router.include_router(folder_hierarchy.router, prefix="/kb/collections", tags=["folder-hierarchy"])
api_router.include_router(simple_upload.router, prefix="/kb", tags=["simple-upload"])
# api_router.include_router(chat.router, prefix="/chat", tags=["chat"])