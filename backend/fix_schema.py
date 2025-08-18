import asyncio
import sqlite3
import sys
from pathlib import Path

# Try to find the database file
possible_paths = [
    "app.db",
    "database.sqlite3", 
    "long_article_writer.db",
    "../database.sqlite3",
    "../app.db"
]

def fix_database_schema():
    db_path = None
    
    # Find the database file
    for path in possible_paths:
        if Path(path).exists():
            db_path = path
            break
    
    if not db_path:
        print("❌ No database file found")
        print("📍 Checking environment for DATABASE_URL...")
        import os
        db_url = os.getenv("DATABASE_URL", "sqlite:///app.db")
        print(f"DATABASE_URL: {db_url}")
        if "sqlite" in db_url:
            # Extract the path from sqlite URL
            db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        return
    
    print(f"✅ Found database: {db_path}")
    
    # Connect and fix schema
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if kb_chunks table exists and get its schema
        cursor.execute("PRAGMA table_info(kb_chunks)")
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ kb_chunks table not found")
            return
            
        print(f"📊 Current kb_chunks columns: {[col[1] for col in columns]}")
        
        # Check if updated_at exists
        has_updated_at = any(col[1] == 'updated_at' for col in columns)
        
        if not has_updated_at:
            print("🔧 Adding missing updated_at column...")
            cursor.execute("""
                ALTER TABLE kb_chunks 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            conn.commit()
            print("✅ Schema fixed!")
        else:
            print("✅ Schema is already correct")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_database_schema()
