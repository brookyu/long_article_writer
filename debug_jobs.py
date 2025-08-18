#!/usr/bin/env python3
"""
Debug script to examine upload_jobs table directly
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import text
from app.core.database import get_db, init_db

async def debug_jobs():
    """Debug upload_jobs table"""
    
    # Initialize database first
    await init_db()
    
    async for db in get_db():
        try:
            # Get recent jobs
            result = await db.execute(text("""
                SELECT job_id, status, total_files, file_list, upload_path
                FROM upload_jobs 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            jobs = result.fetchall()
            
            print("Recent upload jobs:")
            print("=" * 80)
            
            for job in jobs:
                print(f"Job ID: {job[0]}")
                print(f"Status: {job[1]}")
                print(f"Total Files: {job[2]}")
                print(f"File List: {job[3]}")
                print(f"Upload Path: {job[4]}")
                print("-" * 40)
                
            break
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    asyncio.run(debug_jobs())