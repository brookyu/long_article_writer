"""
Simple test script to verify the setup
"""

import asyncio
from app.core.config import get_settings
from app.core.database import init_db, check_database_connection


async def test_setup():
    """Test basic setup"""
    print("Testing configuration...")
    settings = get_settings()
    print(f"✅ Database URL: {settings.DATABASE_URL}")
    print(f"✅ Ollama URL: {settings.ollama_url}")
    print(f"✅ Milvus: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    
    print("\nInitializing database...")
    try:
        await init_db()
        print("✅ Database initialized successfully")
        
        print("\nChecking database connection...")
        if await check_database_connection():
            print("✅ Database connection working")
        else:
            print("❌ Database connection failed")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_setup())