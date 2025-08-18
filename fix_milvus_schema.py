#!/usr/bin/env python3
"""
Script to fix Milvus schema issues by recreating the collection
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pymilvus import connections, Collection, utility, FieldSchema, CollectionSchema, DataType

def fix_milvus_schema():
    """Fix the Milvus collection schema"""
    
    try:
        # Connect to Milvus
        connections.connect("default", host="localhost", port="19530")
        print("✅ Connected to Milvus")
        
        collection_name = "knowledge_base_collection_4"
        
        # Drop existing collection if it exists
        if utility.has_collection(collection_name):
            print(f"🗑️  Dropping existing collection '{collection_name}'")
            utility.drop_collection(collection_name)
        
        # Create new collection with correct schema
        print("🔧 Creating new collection with correct schema...")
        
        # Define fields with correct data types
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="chunk_id", dtype=DataType.INT64, description="Database chunk ID"),
            FieldSchema(name="document_id", dtype=DataType.INT64, description="Database document ID"),
            FieldSchema(name="collection_id", dtype=DataType.INT64, description="Database collection ID"),
            FieldSchema(name="chunk_index", dtype=DataType.INT64, description="Chunk position in document"),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535, description="Chunk text content"),
            FieldSchema(name="char_count", dtype=DataType.INT64, description="Character count"),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=8192, description="JSON metadata"),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384, description="Text embedding")  # Assuming 384 dim for sentence-transformers
        ]
        
        # Create schema
        schema = CollectionSchema(
            fields=fields,
            description=f"Knowledge base collection for collection {collection_name}"
        )
        
        # Create collection
        collection = Collection(name=collection_name, schema=schema)
        print(f"✅ Created collection '{collection_name}' with correct schema")
        
        # Create index for vector field
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        print("✅ Created vector index")
        
        # Load collection
        collection.load()
        print("✅ Collection loaded and ready for use")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        try:
            connections.disconnect("default")
            print("🔌 Disconnected from Milvus")
        except:
            pass

if __name__ == "__main__":
    success = fix_milvus_schema()
    if success:
        print("\n🎉 Milvus schema fixed successfully!")
    else:
        print("\n💥 Failed to fix Milvus schema")
        sys.exit(1)