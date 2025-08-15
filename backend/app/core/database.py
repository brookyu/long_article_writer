"""
Database connection and session management
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import Base

logger = structlog.get_logger(__name__)

# Base is imported from models

# Global variables for database engines and sessions
async_engine = None
async_session_factory = None


def get_async_database_url(database_url: str) -> str:
    """Convert sync database URL to async"""
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+aiomysql://", 1)
    elif database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return database_url


async def init_db() -> None:
    """Initialize database connection and create tables"""
    global async_engine, async_session_factory
    
    settings = get_settings()
    async_url = get_async_database_url(settings.DATABASE_URL)
    
    # Create async engine with different settings for SQLite vs MySQL
    if "sqlite" in async_url:
        async_engine = create_async_engine(
            async_url,
            echo=settings.DEBUG,
        )
    else:
        async_engine = create_async_engine(
            async_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
        )
    
    # Create session factory
    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized", url=async_url.split("@")[1] if "@" in async_url else async_url)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager to get database session"""
    async with get_db() as session:
        yield session


async def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False


async def close_db() -> None:
    """Close database connections"""
    global async_engine
    if async_engine:
        await async_engine.dispose()
        logger.info("Database connections closed")