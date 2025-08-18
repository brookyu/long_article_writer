#!/usr/bin/env python3
"""
Script to add file_list column to upload_jobs table
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import text
from app.core.database import get_db, init_db

async def add_file_list_column():
    # Initialize database first
    await init_db()
    """Add file_list column to upload_jobs table if it doesn't exist"""
    
    async for db in get_db():
        try:
            # Check if column exists
            result = await db.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.columns 
                WHERE table_schema = 'long_article_writer' 
                  AND table_name = 'upload_jobs' 
                  AND column_name = 'file_list'
            """))
            
            count = result.scalar()
            
            if count == 0:
                print("Adding file_list column to upload_jobs table...")
                await db.execute(text("ALTER TABLE upload_jobs ADD COLUMN file_list JSON NULL"))
                await db.commit()
                print("✅ file_list column added successfully!")
            else:
                print("✅ file_list column already exists")
                
            # Verify the column was added
            result = await db.execute(text("DESCRIBE upload_jobs"))
            columns = result.fetchall()
            
            print("\nCurrent upload_jobs table structure:")
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({col[2]})")
                
            break
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await db.rollback()
            break

if __name__ == "__main__":
    asyncio.run(add_file_list_column())