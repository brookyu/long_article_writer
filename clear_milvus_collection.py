#!/usr/bin/env python3
"""
Script to clear corrupted Milvus collection data
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pymilvus import connections, Collection, utility

def clear_milvus_collection():
    """Clear the corrupted Milvus collection"""
    
    try:
        # Connect to Milvus
        connections.connect("default", host="localhost", port="19530")
        print("✅ Connected to Milvus")
        
        collection_name = "knowledge_base_collection_4"
        
        # Check if collection exists
        if utility.has_collection(collection_name):
            print(f"📋 Collection '{collection_name}' exists")
            
            # Drop the collection to clear corrupted data
            utility.drop_collection(collection_name)
            print(f"🗑️  Dropped collection '{collection_name}'")
            
            print("✅ Collection cleared successfully!")
        else:
            print(f"ℹ️  Collection '{collection_name}' does not exist")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        try:
            connections.disconnect("default")
            print("🔌 Disconnected from Milvus")
        except:
            pass
    
    return True

if __name__ == "__main__":
    clear_milvus_collection()