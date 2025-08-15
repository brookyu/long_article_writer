"""
Health check endpoints
"""

from datetime import datetime
from typing import Dict, Any
from http import HTTPStatus

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, check_database_connection

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/", status_code=HTTPStatus.OK)
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "long-article-writer-backend"
    }


@router.get("/detailed", status_code=HTTPStatus.OK)
async def detailed_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Detailed health check with database connectivity"""
    
    # Check database connection
    db_healthy = await check_database_connection()
    
    # Overall health status
    healthy = db_healthy
    status_code = HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE
    
    health_data = {
        "status": "healthy" if healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "long-article-writer-backend",
        "version": "0.1.0",
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy"
        }
    }
    
    if not healthy:
        logger.warning("Health check failed", checks=health_data["checks"])
    
    return health_data