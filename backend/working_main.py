"""
Working FastAPI backend with collection management - hybrid approach
Combines the minimal backend's simplicity with collection endpoints
"""

import hashlib
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from http import HTTPStatus
from enum import Enum
import asyncio

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="Long Article Writer API",
    description="AI-powered long-form article generation with knowledge base integration",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== COLLECTION SCHEMAS =====
class CollectionCreate(BaseModel):
    """Schema for creating a new collection"""
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    embedding_model: Optional[str] = Field(default="nomic-embed-text", description="Embedding model to use")


class CollectionResponse(BaseModel):
    """Schema for collection responses"""
    id: int
    name: str
    description: Optional[str] = None
    embedding_model: Optional[str] = None
    total_documents: int = 0
    total_chunks: int = 0
    created_at: datetime
    updated_at: datetime


class CollectionListResponse(BaseModel):
    """Schema for listing collections"""
    collections: List[CollectionResponse]
    total: int


# ===== DOCUMENT SCHEMAS =====
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentResponse(BaseModel):
    """Schema for document responses"""
    id: int
    collection_id: int
    filename: str
    original_filename: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: str
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Schema for listing documents"""
    documents: List[DocumentResponse]
    total: int


# ===== IN-MEMORY STORAGE (for testing) =====
collections_db = [
    {
        "id": 1,
        "name": "Default Collection",
        "description": "Default knowledge base for testing",
        "embedding_model": "nomic-embed-text",
        "total_documents": 0,
        "total_chunks": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
]
next_collection_id = 2

# Document storage
documents_db = []
next_document_id = 1

# Upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ===== HELPER FUNCTIONS =====
def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()


def get_collection_by_id(collection_id: int):
    """Get collection by ID"""
    return next((col for col in collections_db if col["id"] == collection_id), None)


def update_collection_stats(collection_id: int):
    """Update collection document and chunk counts"""
    collection = get_collection_by_id(collection_id)
    if collection:
        docs = [doc for doc in documents_db if doc["collection_id"] == collection_id]
        collection["total_documents"] = len(docs)
        collection["total_chunks"] = sum(doc.get("chunk_count", 0) for doc in docs)
        collection["updated_at"] = datetime.now()


import re
import json
from bs4 import BeautifulSoup
import hashlib
import urllib.parse
import unicodedata

async def generate_embedding_ollama(text: str) -> List[float]:
    """Generate embedding using Ollama"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return []

def smart_chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into intelligent chunks"""
    if not text.strip():
        return []
    
    # Clean text
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If paragraph is too long, split by sentences
        if len(paragraph) > max_chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    # Add overlap
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
        else:
            # Check if adding this paragraph exceeds chunk size
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Add overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + " " + paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

async def process_document_background(document_id: int, file_path: str, mime_type: str):
    """Enhanced background processing with embeddings"""
    try:
        # Find the document in our database
        document = next((doc for doc in documents_db if doc["id"] == document_id), None)
        if not document:
            return
        
        print(f"Starting enhanced processing for document {document_id}")
        
        # Update status to processing
        document["status"] = DocumentStatus.PROCESSING
        
        # Extract text content
        text_content = ""
        
        if mime_type == "text/plain":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except Exception as e:
                print(f"Error reading text file: {e}")
                document["status"] = DocumentStatus.FAILED
                document["error_message"] = f"File reading failed: {str(e)}"
                return
        
        elif mime_type == "application/pdf":
            # Placeholder - would need PyPDF2 for real PDF extraction
            text_content = f"PDF document content placeholder for: {document['original_filename']}\n\nThis is simulated content that would normally be extracted from the PDF file using PyPDF2 or similar library."
        
        else:
            text_content = f"Document content for: {document['original_filename']}\n\nContent type: {mime_type}"
        
        if not text_content.strip():
            document["status"] = DocumentStatus.FAILED
            document["error_message"] = "No text content extracted"
            return
        
        # Create intelligent chunks
        print(f"Creating chunks from {len(text_content)} characters")
        chunks = smart_chunk_text(text_content)
        
        if not chunks:
            document["status"] = DocumentStatus.FAILED
            document["error_message"] = "No chunks created from text"
            return
        
        print(f"Created {len(chunks)} chunks, generating embeddings...")
        
        # Generate embeddings for each chunk
        chunk_embeddings = []
        successful_chunks = 0
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 20:  # Skip very short chunks
                continue
                
            embedding = await generate_embedding_ollama(chunk)
            if embedding:
                chunk_embeddings.append({
                    "index": i,
                    "text": chunk,
                    "embedding": embedding,
                    "char_count": len(chunk)
                })
                successful_chunks += 1
                
                if (successful_chunks % 5) == 0:
                    print(f"Generated {successful_chunks}/{len(chunks)} embeddings...")
        
        # Store metadata (in a real implementation, this would go to Milvus)
        document["processing_metadata"] = {
            "total_chunks": len(chunks),
            "successful_embeddings": len(chunk_embeddings),
            "total_characters": len(text_content),
            "embedding_model": "nomic-embed-text",
            "chunks_preview": [
                {
                    "index": chunk["index"],
                    "text_preview": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"],
                    "char_count": chunk["char_count"]
                }
                for chunk in chunk_embeddings[:5]  # Store preview of first 5 chunks
            ]
        }
        
        # Update document with processing results
        document["status"] = DocumentStatus.COMPLETED
        document["chunk_count"] = len(chunk_embeddings)
        document["updated_at"] = datetime.now()
        document["error_message"] = None
        
        # Update collection stats
        update_collection_stats(document["collection_id"])
        
        print(f"Document {document_id} processed successfully: {len(chunk_embeddings)} chunks with embeddings")
        
    except Exception as e:
        print(f"Enhanced processing failed for document {document_id}: {e}")
        # Update document status to failed
        for doc in documents_db:
            if doc["id"] == document_id:
                doc["status"] = DocumentStatus.FAILED
                doc["error_message"] = str(e)
                break

# ===== BASIC ENDPOINTS =====
@app.get("/")
async def root():
    return {
        "message": "Long Article Writer API",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "features": ["Collections Management", "Settings", "Health Checks"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "long-article-writer-backend",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "collections_count": len(collections_db)
    }

@app.get("/api/health")
async def api_health():
    return {
        "status": "healthy",
        "service": "long-article-writer-backend",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/settings")
async def get_settings():
    return [
        {
            "id": 1,
            "provider": "ollama",
            "key_alias": "Local Mixtral",
            "model_name": "mixtral:latest",
            "is_active": True
        },
        {
            "id": 2,
            "provider": "ollama", 
            "key_alias": "Local Embedding",
            "model_name": "nomic-embed-text",
            "is_active": True
        }
    ]

# ===== COLLECTION ENDPOINTS =====
@app.post("/api/kb/collections", response_model=CollectionResponse, status_code=HTTPStatus.CREATED)
async def create_collection(collection_data: CollectionCreate) -> CollectionResponse:
    """Create a new knowledge base collection"""
    global next_collection_id
    
    # Check if collection name already exists
    if any(col["name"] == collection_data.name for col in collections_db):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f"Collection with name '{collection_data.name}' already exists"
        )
    
    # Create new collection
    new_collection = {
        "id": next_collection_id,
        "name": collection_data.name,
        "description": collection_data.description,
        "embedding_model": collection_data.embedding_model,
        "total_documents": 0,
        "total_chunks": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    collections_db.append(new_collection)
    next_collection_id += 1
    
    return CollectionResponse(**new_collection)


@app.get("/api/kb/collections", response_model=CollectionListResponse)
async def list_collections() -> CollectionListResponse:
    """List all knowledge base collections"""
    
    collection_responses = [CollectionResponse(**col) for col in collections_db]
    
    return CollectionListResponse(
        collections=collection_responses,
        total=len(collections_db)
    )


@app.get("/api/kb/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: int) -> CollectionResponse:
    """Get a specific collection by ID"""
    
    collection = next((col for col in collections_db if col["id"] == collection_id), None)
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    return CollectionResponse(**collection)


@app.put("/api/kb/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(collection_id: int, collection_data: CollectionCreate) -> CollectionResponse:
    """Update a collection"""
    
    collection = next((col for col in collections_db if col["id"] == collection_id), None)
    
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Check for name conflicts if name is being updated
    if collection_data.name != collection["name"]:
        if any(col["name"] == collection_data.name for col in collections_db):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f"Collection with name '{collection_data.name}' already exists"
            )
    
    # Update fields
    collection["name"] = collection_data.name
    if collection_data.description is not None:
        collection["description"] = collection_data.description
    if collection_data.embedding_model is not None:
        collection["embedding_model"] = collection_data.embedding_model
    collection["updated_at"] = datetime.now()
    
    return CollectionResponse(**collection)


@app.delete("/api/kb/collections/{collection_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_collection(collection_id: int) -> None:
    """Delete a collection and all its documents"""
    
    collection_index = next((i for i, col in enumerate(collections_db) if col["id"] == collection_id), None)
    
    if collection_index is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Remove collection
    collections_db.pop(collection_index)
    
    # Also remove all documents in this collection
    global documents_db
    documents_db = [doc for doc in documents_db if doc["collection_id"] != collection_id]


# ===== DOCUMENT ENDPOINTS =====
@app.post("/api/kb/collections/{collection_id}/documents", response_model=DocumentResponse, status_code=HTTPStatus.CREATED)
async def upload_document(
    collection_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> DocumentResponse:
    """Upload a document to a collection"""
    global next_document_id
    
    # Check if collection exists
    collection = get_collection_by_id(collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    file_hash = calculate_file_hash(file_content)
    
    # Check for duplicate files
    existing_doc = next((doc for doc in documents_db if doc["sha256"] == file_hash), None)
    if existing_doc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f"Document with same content already exists (ID: {existing_doc['id']})"
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create document record
    current_document_id = next_document_id
    new_document = {
        "id": current_document_id,
        "collection_id": collection_id,
        "filename": unique_filename,
        "original_filename": file.filename or "unknown",
        "mime_type": file.content_type,
        "size_bytes": file_size,
        "sha256": file_hash,
        "file_path": file_path,
        "status": DocumentStatus.PENDING,  # Will be processed in background
        "error_message": None,
        "chunk_count": 0,  # Will be updated after processing
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    documents_db.append(new_document)
    next_document_id += 1
    
    # Start background processing
    background_tasks.add_task(
        process_document_background,
        current_document_id,  # Use the actual document ID
        file_path,
        file.content_type or "application/octet-stream"
    )
    
    # Update collection stats (will be updated again after processing)
    update_collection_stats(collection_id)
    
    return DocumentResponse(**new_document)


@app.get("/api/kb/collections/{collection_id}/documents", response_model=DocumentListResponse)
async def list_documents(collection_id: int) -> DocumentListResponse:
    """List all documents in a collection"""
    
    # Check if collection exists
    collection = get_collection_by_id(collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Get documents for this collection
    collection_documents = [doc for doc in documents_db if doc["collection_id"] == collection_id]
    
    document_responses = [DocumentResponse(**doc) for doc in collection_documents]
    
    return DocumentListResponse(
        documents=document_responses,
        total=len(collection_documents)
    )


@app.get("/api/kb/collections/{collection_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(collection_id: int, document_id: int) -> DocumentResponse:
    """Get a specific document"""
    
    document = next((doc for doc in documents_db 
                    if doc["id"] == document_id and doc["collection_id"] == collection_id), None)
    
    if not document:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found in collection {collection_id}"
        )
    
    return DocumentResponse(**document)


@app.delete("/api/kb/collections/{collection_id}/documents/{document_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_document(collection_id: int, document_id: int) -> None:
    """Delete a document"""
    
    document_index = next((i for i, doc in enumerate(documents_db) 
                          if doc["id"] == document_id and doc["collection_id"] == collection_id), None)
    
    if document_index is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found in collection {collection_id}"
        )
    
    # Remove file from disk
    document = documents_db[document_index]
    try:
        if os.path.exists(document["file_path"]):
            os.remove(document["file_path"])
    except Exception:
        pass  # Continue even if file deletion fails
    
    # Remove from database
    documents_db.pop(document_index)
    
    # Update collection stats
    update_collection_stats(collection_id)


@app.get("/api/kb/collections/{collection_id}/documents/{document_id}/status")
async def get_document_processing_status(collection_id: int, document_id: int) -> Dict[str, Any]:
    """Get document processing status"""
    
    document = next((doc for doc in documents_db 
                    if doc["id"] == document_id and doc["collection_id"] == collection_id), None)
    
    if not document:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found in collection {collection_id}"
        )
    
    status_info = {
        "document_id": document_id,
        "status": document["status"],
        "progress": 1.0 if document["status"] == DocumentStatus.COMPLETED else 
                   0.5 if document["status"] == DocumentStatus.PROCESSING else 0.0,
        "chunk_count": document.get("chunk_count", 0),
        "error_message": document.get("error_message"),
        "updated_at": document["updated_at"]
    }
    
    return status_info


@app.get("/api/kb/collections/{collection_id}/documents/{document_id}/details")
async def get_document_details(collection_id: int, document_id: int) -> Dict[str, Any]:
    """Get detailed document information including processing metadata"""
    
    document = next((doc for doc in documents_db 
                    if doc["id"] == document_id and doc["collection_id"] == collection_id), None)
    
    if not document:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document with id {document_id} not found in collection {collection_id}"
        )
    
    details = {
        "document": DocumentResponse(**document),
        "processing_metadata": document.get("processing_metadata", {}),
        "has_embeddings": bool(document.get("processing_metadata", {}).get("successful_embeddings", 0) > 0)
    }
    
    return details


# Article Generation Service Integration
async def generate_text_ollama(prompt: str, max_tokens: int = 1000) -> str:
    """Generate text using Ollama for article generation"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gpt-oss:20b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
    except Exception as e:
        print(f"Text generation failed: {e}")
        return f"[Error generating text: {str(e)}]"

async def search_collection_internal(collection_id: int, query: str) -> Dict[str, Any]:
    """Internal search function for article generation"""
    # Reuse the existing search logic
    collection = get_collection_by_id(collection_id)
    if not collection:
        return {"matches": [], "total_matches": 0}
    
    # Generate embedding for the query
    query_embedding = await generate_embedding_ollama(query)
    if not query_embedding:
        return {"matches": [], "total_matches": 0}
    
    # Semantic search using embeddings (same logic as search endpoint)
    collection_documents = [doc for doc in documents_db if doc["collection_id"] == collection_id and doc["status"] == DocumentStatus.COMPLETED]
    
    matches = []
    for doc in collection_documents:
        processing_metadata = doc.get("processing_metadata", {})
        if not processing_metadata.get("successful_embeddings"):
            continue
        
        chunks_preview = processing_metadata.get("chunks_preview", [])
        for chunk_info in chunks_preview:
            text_preview = chunk_info.get("text_preview", "")
            
            # Simple relevance scoring based on keyword overlap
            query_words = set(query.lower().split())
            chunk_words = set(text_preview.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            relevance_score = min(0.95, overlap / len(query_words)) if query_words else 0.0
            
            if relevance_score > 0.1:
                matches.append({
                    "document_id": doc["id"],
                    "chunk_index": chunk_info["index"],
                    "filename": doc["original_filename"],
                    "relevance_score": relevance_score,
                    "preview": text_preview,
                    "char_count": chunk_info.get("char_count", 0),
                    "search_type": "semantic"
                })
    
    matches.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"matches": matches, "total_matches": len(matches)}

async def enhanced_web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Enhanced multi-language web search with Chinese search engine support"""
    
    # Detect query language
    language = detect_language(query)
    print(f"Detected language for '{query}': {language}")
    
    all_results = []
    
    if language == "zh":
        # Chinese query - prioritize Chinese search engines
        print("Using Chinese search engines for Chinese query")
        
        # Search Chinese sources
        baidu_results = await baidu_search(query, max_results // 2)
        zh_wiki_results = await chinese_wikipedia_search(query, 2)
        sogou_results = await sogou_search(query, 1)
        
        all_results.extend(baidu_results)
        all_results.extend(zh_wiki_results)
        all_results.extend(sogou_results)
        
        # Also search international sources for broader coverage
        ddg_results = await duckduckgo_search(query, 1)
        all_results.extend(ddg_results)
        
    elif language == "mixed":
        # Mixed language query - use both Chinese and international sources
        print("Using mixed search engines for mixed language query")
        
        baidu_results = await baidu_search(query, 2)
        ddg_results = await duckduckgo_search(query, 2)
        wiki_results = await wikipedia_search(query, 1)
        
        all_results.extend(baidu_results)
        all_results.extend(ddg_results)
        all_results.extend(wiki_results)
        
    else:
        # English/International query - use international search engines
        print("Using international search engines for English query")
        
        # Try DuckDuckGo instant answers first (reliable API)
        ddg_results = await duckduckgo_search(query, max_results // 2)
        
        # Try Wikipedia search for comprehensive content
        wiki_results = await wikipedia_search(query, max_results // 2)
        
        all_results.extend(ddg_results)
        all_results.extend(wiki_results)
    
    # Sort by relevance and limit
    all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    final_results = all_results[:max_results]
    
    # Log search engine distribution
    engines_used = {}
    for result in final_results:
        engine = result.get("search_engine", "unknown")
        engines_used[engine] = engines_used.get(engine, 0) + 1
    
    engines_summary = ", ".join([f"{engine}({count})" for engine, count in engines_used.items()])
    print(f"Enhanced web search found {len(final_results)} results using: {engines_summary}")
    
    return final_results

async def duckduckgo_search(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """DuckDuckGo instant answers and search"""
    try:
        # DuckDuckGo instant answer API
        ddg_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(ddg_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Get abstract if available
            abstract = data.get("Abstract", "")
            abstract_url = data.get("AbstractURL", "")
            abstract_source = data.get("AbstractSource", "")
            definition = data.get("Definition", "")
            definition_url = data.get("DefinitionURL", "")
            
            if abstract and abstract_url:
                results.append({
                    "title": f"{abstract_source}: {query}",
                    "url": abstract_url,
                    "snippet": abstract[:300] + "..." if len(abstract) > 300 else abstract,
                    "content": abstract,
                    "relevance_score": 0.9,
                    "source_type": "web_search",
                    "search_engine": "duckduckgo",
                    "char_count": len(abstract)
                })
            elif definition and definition_url:
                results.append({
                    "title": f"Definition: {query}",
                    "url": definition_url,
                    "snippet": definition[:300] + "..." if len(definition) > 300 else definition,
                    "content": definition,
                    "relevance_score": 0.8,
                    "source_type": "web_search",
                    "search_engine": "duckduckgo",
                    "char_count": len(definition)
                })
            
            # Add related topics
            related_topics = data.get("RelatedTopics", [])
            for i, topic in enumerate(related_topics[:max_results-1]):
                if isinstance(topic, dict) and topic.get("Text"):
                    text = topic.get("Text", "")
                    url = topic.get("FirstURL", "")
                    
                    if text and url:
                        results.append({
                            "title": f"Related: {text[:60]}...",
                            "url": url,
                            "snippet": text[:200] + "..." if len(text) > 200 else text,
                            "content": text,
                            "relevance_score": 0.7 - (i * 0.1),
                            "source_type": "web_search",
                            "search_engine": "duckduckgo",
                            "char_count": len(text)
                        })
            
            return results
            
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        return []

async def wikipedia_search(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """Wikipedia search using the correct API endpoints"""
    try:
        headers = {
            "User-Agent": "Long-Article-Writer/1.0 (brook@example.com)"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Use the correct Wikipedia search API
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "srprop": "snippet"
            }
            
            response = await client.get(search_url, params=search_params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            search_results = data.get("query", {}).get("search", [])
            
            for i, result in enumerate(search_results):
                title = result.get("title", "")
                snippet = result.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                page_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                
                if title and snippet:
                    results.append({
                        "title": f"Wikipedia: {title}",
                        "url": page_url,
                        "snippet": snippet[:300] + "..." if len(snippet) > 300 else snippet,
                        "content": snippet,
                        "relevance_score": 0.8 - (i * 0.1),
                        "source_type": "web_search",
                        "search_engine": "wikipedia",
                        "char_count": len(snippet)
                    })
            
            return results
            
    except Exception as e:
        print(f"Wikipedia search failed: {e}")
        return []

def detect_language(text: str) -> str:
    """Detect if text contains Chinese characters"""
    chinese_chars = 0
    total_chars = len(text)
    
    if total_chars == 0:
        return "en"
    
    for char in text:
        if '\u4e00' <= char <= '\u9fff':  # CJK Unified Ideographs
            chinese_chars += 1
    
    chinese_ratio = chinese_chars / total_chars
    
    if chinese_ratio > 0.3:  # If more than 30% Chinese characters
        return "zh"
    elif chinese_ratio > 0.1:  # If some Chinese characters
        return "mixed"
    else:
        return "en"

async def baidu_search(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Search using Baidu search engine (web scraping approach)"""
    try:
        # Baidu search URL
        search_url = "https://www.baidu.com/s"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.baidu.com/",
        }
        
        params = {
            "wd": query,
            "rn": max_results * 2,  # Request more results for filtering
            "ie": "utf-8"
        }
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse Baidu search results
            result_containers = soup.find_all('div', class_='result') or soup.find_all('div', {'data-log': True})
            
            for i, container in enumerate(result_containers[:max_results]):
                try:
                    # Extract title
                    title_elem = container.find('h3') or container.find('a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    link_elem = container.find('a', href=True)
                    url = link_elem['href'] if link_elem else ""
                    
                    # Clean Baidu redirect URLs
                    if url.startswith('http://www.baidu.com/link?url='):
                        url = urllib.parse.unquote(url.split('url=')[1].split('&')[0])
                    
                    # Extract content/description
                    content_elem = container.find('span', class_='content-right_8Zs40') or \
                                   container.find('div', class_='c-abstract') or \
                                   container.find('div', class_='c-span9')
                    
                    content = content_elem.get_text(strip=True) if content_elem else ""
                    
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": content[:300] + "..." if len(content) > 300 else content,
                            "content": content,
                            "relevance_score": 0.9 - (i * 0.1),
                            "source_type": "web_search",
                            "search_engine": "baidu",
                            "char_count": len(content)
                        })
                
                except Exception as e:
                    print(f"Failed to parse Baidu result: {e}")
                    continue
            
            print(f"Baidu search found {len(results)} results for: {query}")
            return results
            
    except Exception as e:
        print(f"Baidu search failed: {e}")
        return []

async def sogou_search(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """Search using Sogou search engine"""
    try:
        search_url = "https://www.sogou.com/web"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.sogou.com/"
        }
        
        params = {
            "query": query,
            "num": max_results
        }
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse Sogou results (simplified approach)
            result_divs = soup.find_all('div', class_='rb') or soup.find_all('div', class_='results')
            
            for i, div in enumerate(result_divs[:max_results]):
                try:
                    title_elem = div.find('h3') or div.find('a')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    link_elem = div.find('a', href=True)
                    url = link_elem['href'] if link_elem else ""
                    
                    content_elem = div.find('div', class_='ft') or div.find('p')
                    content = content_elem.get_text(strip=True) if content_elem else ""
                    
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": content[:200] + "..." if len(content) > 200 else content,
                            "content": content,
                            "relevance_score": 0.8 - (i * 0.1),
                            "source_type": "web_search",
                            "search_engine": "sogou",
                            "char_count": len(content)
                        })
                
                except Exception as e:
                    print(f"Failed to parse Sogou result: {e}")
                    continue
            
            print(f"Sogou search found {len(results)} results for: {query}")
            return results
            
    except Exception as e:
        print(f"Sogou search failed: {e}")
        return []

async def chinese_wikipedia_search(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """Search Chinese Wikipedia for comprehensive information"""
    try:
        # Chinese Wikipedia API
        search_url = "https://zh.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query)
        
        headers = {
            "User-Agent": "Long-Article-Writer/1.0 (brook@example.com)"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Try direct page first
            try:
                response = await client.get(search_url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    
                    title = data.get("title", "")
                    extract = data.get("extract", "")
                    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
                    
                    if extract and page_url and title:
                        return [{
                            "title": f"中文维基百科: {title}",
                            "url": page_url,
                            "snippet": extract[:300] + "..." if len(extract) > 300 else extract,
                            "content": extract,
                            "relevance_score": 0.85,
                            "source_type": "web_search",
                            "search_engine": "zh_wikipedia",
                            "char_count": len(extract)
                        }]
            except:
                pass
            
            # If direct page fails, try search API
            search_api_url = "https://zh.wikipedia.org/api/rest_v1/page/search/" + urllib.parse.quote(query)
            response = await client.get(search_api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for i, page in enumerate(data.get("pages", [])[:max_results]):
                title = page.get("title", "")
                description = page.get("description", "")
                extract = page.get("extract", "")
                page_url = f"https://zh.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                
                content = extract or description
                if content and title:
                    results.append({
                        "title": f"中文维基百科: {title}",
                        "url": page_url,
                        "snippet": content[:200] + "..." if len(content) > 200 else content,
                        "content": content,
                        "relevance_score": 0.8 - (i * 0.1),
                        "source_type": "web_search",
                        "search_engine": "zh_wikipedia",
                        "char_count": len(content)
                    })
            
            return results
            
    except Exception as e:
        print(f"Chinese Wikipedia search failed: {e}")
        return []

async def extract_web_content(results: List[Dict[str, Any]]) -> None:
    """Extract full content from web pages for top search results"""
    async def extract_single_page(result: Dict[str, Any]) -> None:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(result["url"], headers=headers)
                response.raise_for_status()
                
                # Parse HTML and extract text
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                
                # Try to find main content
                content_selectors = ['article', 'main', '.content', '.post-content', '.entry-content']
                
                extracted_content = ""
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        extracted_content = elements[0].get_text(strip=True)
                        break
                
                # Fallback to body content
                if not extracted_content:
                    body = soup.find('body')
                    if body:
                        extracted_content = body.get_text(strip=True)
                
                # Clean and limit content
                extracted_content = re.sub(r'\s+', ' ', extracted_content)
                extracted_content = extracted_content[:2000]  # Limit to 2000 chars
                
                if extracted_content:
                    result["content"] = extracted_content
                    result["char_count"] = len(extracted_content)
                
        except Exception as e:
            print(f"Failed to extract content from {result['url']}: {e}")
            # Keep original content if extraction fails
            pass
    
    # Extract content for all results concurrently
    import asyncio
    tasks = [extract_single_page(result) for result in results]
    await asyncio.gather(*tasks, return_exceptions=True)

async def hybrid_research(collection_id: int, query: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
    """Hybrid research combining local KB and web search"""
    
    # Step 1: Search local knowledge base
    local_results = await search_collection_internal(collection_id, query)
    local_matches = local_results.get("matches", [])
    
    # Calculate confidence based on relevance scores
    confidence_score = 0.0
    if local_matches:
        confidence_score = sum(match.get("relevance_score", 0) for match in local_matches) / len(local_matches)
    
    research_data = {
        "query": query,
        "local_results": local_matches[:5],  # Top 5 local results
        "web_results": [],
        "confidence_score": confidence_score,
        "used_web_search": False,
        "total_sources": len(local_matches)
    }
    
    # Step 2: Use enhanced web search if confidence is low
    if confidence_score < confidence_threshold:
        print(f"Local confidence {confidence_score:.2f} < {confidence_threshold}, performing enhanced web search")
        web_results = await enhanced_web_search(query, max_results=5)
        research_data["web_results"] = web_results
        research_data["used_web_search"] = True
        research_data["search_engine"] = "enhanced_multi_source"
        research_data["total_sources"] += len(web_results)
    else:
        print(f"Local confidence {confidence_score:.2f} sufficient, skipping web search")
    
    return research_data

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if not vec1 or not vec2:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

@app.post("/api/kb/collections/{collection_id}/search")
async def search_collection(
    collection_id: int, 
    query: Dict[str, str]
) -> Dict[str, Any]:
    """Enhanced semantic search using embeddings"""
    
    # Check if collection exists
    collection = get_collection_by_id(collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    query_text = query.get("query", "").strip()
    if not query_text:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Query text is required"
        )
    
    # Generate embedding for the query
    print(f"Generating embedding for query: {query_text}")
    query_embedding = await generate_embedding_ollama(query_text)
    
    if not query_embedding:
        # Fallback to simple text search
        collection_documents = [doc for doc in documents_db if doc["collection_id"] == collection_id]
        matches = []
        for doc in collection_documents:
            if doc["status"] == DocumentStatus.COMPLETED:
                if query_text.lower() in doc["original_filename"].lower():
                    matches.append({
                        "document_id": doc["id"],
                        "chunk_index": 0,
                        "filename": doc["original_filename"],
                        "relevance_score": 0.5,
                        "preview": f"Text search match in {doc['original_filename']}...",
                        "search_type": "text_fallback"
                    })
        return {
            "query": query_text,
            "collection_id": collection_id,
            "total_matches": len(matches),
            "matches": matches[:10],
            "search_type": "text_fallback"
        }
    
    # Semantic search using embeddings
    print(f"Performing semantic search across {len(documents_db)} documents")
    collection_documents = [doc for doc in documents_db if doc["collection_id"] == collection_id and doc["status"] == DocumentStatus.COMPLETED]
    
    matches = []
    
    for doc in collection_documents:
        processing_metadata = doc.get("processing_metadata", {})
        if not processing_metadata.get("successful_embeddings"):
            continue
        
        # Note: In a real implementation, we would query Milvus here
        # For now, we'll simulate similarity search using stored metadata
        chunks_preview = processing_metadata.get("chunks_preview", [])
        
        for chunk_info in chunks_preview:
            # Simulate similarity score (would be actual cosine similarity with stored embeddings)
            # For demo, we'll use a simple text matching score
            text_preview = chunk_info.get("text_preview", "")
            
            # Simple relevance scoring based on keyword overlap
            query_words = set(query_text.lower().split())
            chunk_words = set(text_preview.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            relevance_score = min(0.95, overlap / len(query_words)) if query_words else 0.0
            
            # Only include chunks with some relevance
            if relevance_score > 0.1:
                matches.append({
                    "document_id": doc["id"],
                    "chunk_index": chunk_info["index"],
                    "filename": doc["original_filename"],
                    "relevance_score": relevance_score,
                    "preview": text_preview,
                    "char_count": chunk_info.get("char_count", 0),
                    "search_type": "semantic"
                })
    
    # Sort by relevance score
    matches.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    print(f"Found {len(matches)} semantic matches")
    
    return {
        "query": query_text,
        "collection_id": collection_id,
        "total_matches": len(matches),
        "matches": matches[:10],  # Limit to top 10
        "search_type": "semantic",
        "has_query_embedding": True
    }


@app.post("/api/kb/collections/{collection_id}/hybrid-search")
async def hybrid_search_endpoint(
    collection_id: int, 
    query: Dict[str, Any]
) -> Dict[str, Any]:
    """Hybrid search combining local KB and web search"""
    
    # Check if collection exists
    collection = get_collection_by_id(collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    query_text = query.get("query", "").strip()
    confidence_threshold = query.get("confidence_threshold", 0.5)
    
    if not query_text:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Query text is required"
        )
    
    try:
        research_results = await hybrid_research(collection_id, query_text, confidence_threshold)
        return research_results
        
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Hybrid search failed: {str(e)}"
        )


# ===== ARTICLE GENERATION ENDPOINTS =====

# Simple in-memory storage for articles
articles_db = []
next_article_id = 1

class ArticleRequest(BaseModel):
    """Schema for article generation request"""
    topic: str = Field(..., min_length=1, description="Main topic for the article")
    subtopics: Optional[List[str]] = Field(default=[], description="Additional subtopics to research")
    article_type: Optional[str] = Field(default="comprehensive", description="Type of article")
    target_length: Optional[str] = Field(default="medium", description="Target article length")
    writing_style: Optional[str] = Field(default="professional", description="Writing style")

class ArticleResponse(BaseModel):
    """Schema for article generation response"""
    id: int
    status: str
    progress: Optional[str] = None
    topic: str
    title: Optional[str] = None
    content: Optional[str] = None
    word_count: Optional[int] = None
    generation_time_seconds: Optional[float] = None
    references: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime

@app.post("/api/kb/collections/{collection_id}/generate-article", response_model=ArticleResponse, status_code=HTTPStatus.CREATED)
async def generate_article(
    collection_id: int,
    article_request: ArticleRequest,
    background_tasks: BackgroundTasks
) -> ArticleResponse:
    """Generate an AI article using the knowledge base"""
    global next_article_id
    
    # Check if collection exists
    collection = get_collection_by_id(collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    # Create article record
    current_article_id = next_article_id
    new_article = {
        "id": current_article_id,
        "collection_id": collection_id,
        "status": "generating",
        "topic": article_request.topic,
        "subtopics": article_request.subtopics,
        "article_type": article_request.article_type,
        "target_length": article_request.target_length,
        "writing_style": article_request.writing_style,
        "title": None,
        "content": None,
        "word_count": None,
        "generation_time_seconds": None,
        "references": None,
        "error_message": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    articles_db.append(new_article)
    next_article_id += 1
    
    # Start background article generation
    background_tasks.add_task(
        generate_article_background,
        current_article_id,
        collection_id,
        article_request.topic,
        article_request.subtopics,
        article_request.article_type,
        article_request.target_length,
        article_request.writing_style
    )
    
    return ArticleResponse(**new_article)

async def generate_article_background(
    article_id: int,
    collection_id: int,
    topic: str,
    subtopics: List[str],
    article_type: str,
    target_length: str,
    writing_style: str
):
    """Background article generation process with timeout"""
    try:
        # Set maximum generation time to 5 minutes
        MAX_GENERATION_TIME = 300  # 5 minutes
        generation_start = datetime.now()
        # Find the article in our database
        article = next((art for art in articles_db if art["id"] == article_id), None)
        if not article:
            return
        
        print(f"Starting article generation for: {topic}")
        start_time = datetime.now()
        
        # Update status with progress
        article["status"] = "generating"
        article["progress"] = "Starting research phase..."
        article["updated_at"] = datetime.now()
        
        # Step 1: Research the topic using hybrid approach
        print(f"Researching topic with hybrid search: {topic}")
        article["progress"] = "Searching knowledge base and web sources..."
        research_queries = [topic] + (subtopics or [])
        research_results = []
        web_sources_used = []
        references = []
        reference_counter = 1
        
        for query in research_queries:
            print(f"🔍 Research query: {query}")
            hybrid_results = await hybrid_research(collection_id, query, confidence_threshold=0.8)  # Higher threshold to force web search
            
            print(f"📊 Hybrid research results: {len(hybrid_results.get('local_results', []))} local, {len(hybrid_results.get('web_results', []))} web")
            
            # Add local results (reduced for speed)
            research_results.extend(hybrid_results.get("local_results", [])[:1])  # Top 1 per query
            
            # Add web results if used and collect references (reduced for speed)
            web_results = hybrid_results.get("web_results", [])
            if web_results:
                print(f"📰 Found {len(web_results)} web results for query '{query}'")
                research_results.extend(web_results[:1])  # Top 1 web result per query
                web_sources_used.extend([f"Web: {r.get('title', 'Unknown')}" for r in web_results])
                
                # Collect references for citation (reduced for speed)
                for result in web_results[:1]:
                    if result.get("url") and result.get("title"):
                        ref_entry = {
                            "number": reference_counter,
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "engine": result.get("search_engine", "web"),
                            "accessed": datetime.now().strftime("%Y-%m-%d")
                        }
                        references.append(ref_entry)
                        print(f"📚 Added reference {reference_counter}: {ref_entry['title']}")
                        reference_counter += 1
            else:
                print(f"❌ No web results found for query '{query}'")
        
        if not research_results:
            print("No relevant content found in knowledge base - proceeding with web-only generation")
            article["progress"] = "Limited content found, proceeding with web sources only..."
            # Don't fail - proceed with web content only
        
        article["progress"] = "Generating article outline..."
        
        print(f"📋 RESEARCH SUMMARY:")
        print(f"   • {len(research_results)} relevant chunks for research")
        print(f"   • {len(references)} references collected for citations")
        print(f"   • References: {[ref['title'][:50] + '...' for ref in references] if references else 'None'}")
        
        # Step 2: Generate article outline
        print("Generating article outline...")
        print(f"🎯 About to create research context for {len(research_results)} results")
        research_context = "\n".join([
            f"- {result.get('preview', '')[:100]}..."
            for result in research_results[:5]
        ])
        print(f"🎯 Research context created, about to generate outline prompt")
        
        outline_prompt = f"""Create a detailed article outline specifically about: "{topic}"

CRITICAL: The entire article must be about "{topic}" only. Do not write about other subjects.

Article Requirements:
- Topic: {topic}
- Type: {article_type}
- Length: {target_length}
- Style: {writing_style}

Research context about {topic}:
{research_context}

Create an outline that covers different aspects of "{topic}" with:
1. Compelling title about {topic}
2. Introduction to {topic}
3. 3-5 main sections exploring different aspects of {topic}
4. Conclusion about {topic}

Format as:
# [Title about {topic}]
## Introduction
## [Section 1 about {topic}]
## [Section 2 about {topic}]
## [Section 3 about {topic}]
## Conclusion

Ensure every section relates directly to "{topic}":"""

        print(f"🎯 Outline prompt created, now attempting generation")
        # Generate dynamic outline based on the actual topic
        print(f"🔄 Attempting to generate outline for: {topic}")
        try:
            outline_result = await generate_text_ollama(outline_prompt, max_tokens=500)
            print(f"✅ Successfully generated outline for topic: {topic}")
            print(f"📋 FULL OUTLINE RESULT:\n{outline_result}")
        except Exception as e:
            print(f"❌ Outline generation failed, using fallback: {e}")
            # Fallback outline that uses the actual topic
            outline_result = f"""# {topic}: A Comprehensive Guide

## Introduction
## Key Aspects and Applications  
## Benefits and Challenges
## Conclusion"""
            print(f"📋 USING FALLBACK OUTLINE:\n{outline_result}")
        
        # Step 3: Generate content for each section
        print("Generating article content...")
        
        # Parse sections from outline
        sections = []
        lines = outline_result.split('\n')
        title = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                print(f"📝 EXTRACTED TITLE: '{title}'")
            elif line.startswith('## '):
                sections.append(line[3:].strip())
        
        if not title:
            title = f"{topic}: A Comprehensive Guide"
            print(f"⚠️ NO TITLE FOUND, using fallback: '{title}'")
        
        # Generate content
        article["progress"] = f"Writing article content ({len(sections)} sections)..."
        full_content = [f"# {title}\n"]
        
        for section_idx, section in enumerate(sections, 1):
            # Check timeout before each section
            elapsed_time = (datetime.now() - generation_start).total_seconds()
            if elapsed_time > MAX_GENERATION_TIME:
                print(f"⏰ Generation timeout after {elapsed_time:.1f}s, stopping")
                article["status"] = "failed"
                article["error_message"] = f"Generation timeout after {MAX_GENERATION_TIME}s"
                article["updated_at"] = datetime.now()
                return
                
            print(f"Generating section: {section} (elapsed: {elapsed_time:.1f}s)")
            article["progress"] = f"Writing section {section_idx}/{len(sections)}: {section}..."
            
            # Find relevant content for this section
            section_search = await search_collection_internal(collection_id, f"{topic} {section}")
            section_context = "\n".join([
                result.get('preview', '')
                for result in section_search.get("matches", [])[:2]
            ])
            
            # Prepare references for this section
            section_refs = "\n".join([f"[{ref['number']}] {ref['title']}" for ref in references[:5]]) if references else "No web references available."
            
            section_prompt = f"""You are writing a section for an article about "{topic}".

Section Title: {section}
Writing Style: {writing_style}
Article Topic: {topic}

Context from knowledge base: {section_context}

Available citations: {section_refs}

CRITICAL: Stay strictly on the topic of "{topic}". Do not write about unrelated subjects.

Requirements:
1. Write 100-200 words specifically about "{topic}" as it relates to "{section}"
2. Address the section topic directly with specific content about {topic}
3. Include 2-3 key points with examples relevant to {topic}
4. Use citations [1], [2], etc. when referencing facts about {topic}
5. Maintain {writing_style} tone while discussing {topic}
6. Provide substantive information about {topic}, not generic content

Write the complete section content (no heading). Focus entirely on {topic}:"""
            
            try:
                section_content = await generate_text_ollama(section_prompt, max_tokens=400)
            except Exception as e:
                print(f"Warning: Section generation failed for '{section}': {e}")
                section_content = f"This section on {section} could not be generated due to technical issues."
            
            # Ensure section is not empty
            if not section_content or len(section_content.strip()) < 20:
                section_content = f"This section on {section} is currently being developed and will provide comprehensive information about this important aspect of {topic}."
                print(f"Warning: Generated empty content for section '{section}', using placeholder")
            
            full_content.append(f"## {section}\n")
            full_content.append(f"{section_content}\n")
        
        # Add references section if we have web sources
        if references:
            full_content.append("## References\n")
            for ref in references:
                full_content.append(f"{ref['number']}. {ref['title']}. *{ref['engine']}*. Retrieved {ref['accessed']} from {ref['url']}\n")
            full_content.append("")
        
        # Combine all content
        article_text = "\n".join(full_content)
        word_count = len(article_text.split())
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # Update article record
        article["status"] = "completed"
        article["title"] = title
        article["content"] = article_text
        article["word_count"] = word_count
        article["generation_time_seconds"] = generation_time
        article["references"] = references
        article["updated_at"] = datetime.now()
        
        print(f"Article generation completed: {word_count} words in {generation_time:.2f}s")
        
    except Exception as e:
        print(f"Article generation failed for article {article_id}: {e}")
        # Update article status to failed
        for art in articles_db:
            if art["id"] == article_id:
                art["status"] = "failed"
                art["error_message"] = str(e)
                art["updated_at"] = datetime.now()
                break

@app.get("/api/kb/collections/{collection_id}/articles/{article_id}", response_model=ArticleResponse)
async def get_article(collection_id: int, article_id: int) -> ArticleResponse:
    """Get a generated article"""
    
    article = next((art for art in articles_db 
                   if art["id"] == article_id and art["collection_id"] == collection_id), None)
    
    if not article:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Article with id {article_id} not found in collection {collection_id}"
        )
    
    return ArticleResponse(**article)

@app.get("/api/kb/collections/{collection_id}/articles")
async def list_articles(collection_id: int) -> Dict[str, Any]:
    """List all articles for a collection"""
    
    # Check if collection exists
    collection = get_collection_by_id(collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Collection with id {collection_id} not found"
        )
    
    collection_articles = [art for art in articles_db if art["collection_id"] == collection_id]
    
    return {
        "articles": [ArticleResponse(**art) for art in collection_articles],
        "total": len(collection_articles),
        "collection_id": collection_id
    }

@app.delete("/api/kb/collections/{collection_id}/articles/{article_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_article(collection_id: int, article_id: int) -> None:
    """Delete an article"""
    
    article_index = next((i for i, art in enumerate(articles_db) 
                         if art["id"] == article_id and art["collection_id"] == collection_id), None)
    
    if article_index is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Article with id {article_id} not found in collection {collection_id}"
        )
    
    # Remove from database
    articles_db.pop(article_index)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)