#!/usr/bin/env python3
"""
Test script for enhanced file format support
"""

import asyncio
import sys
import os
sys.path.append('./backend')

from backend.app.services.text_processing import DocumentProcessor, document_analyzer

async def test_file_format(file_path: str):
    """Test processing a specific file"""
    print(f"\n{'='*60}")
    print(f"Testing: {file_path}")
    print(f"{'='*60}")
    
    try:
        processor = DocumentProcessor()
        
        # Test validation
        validation = await processor.validate_file(file_path)
        print(f"Validation: {'✅ PASS' if validation['valid'] else '❌ FAIL'}")
        if validation['errors']:
            print(f"Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
        
        file_info = validation['file_info']
        print(f"File Info: {file_info}")
        
        # Test MIME detection
        mime_type = await processor.detect_mime_type(file_path)
        print(f"MIME Type: {mime_type}")
        
        # Test text extraction
        extracted_text = await processor.extract_text_from_file(file_path)
        print(f"Extracted Text Length: {len(extracted_text)} characters")
        print(f"First 200 characters:")
        print(f"'{extracted_text[:200]}...'")
        
        # Test chunking
        chunks = processor.create_chunks(extracted_text)
        print(f"Created {len(chunks)} chunks")
        if chunks:
            print(f"First chunk: '{chunks[0].text[:100]}...'")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Test all supported formats"""
    test_files = [
        './test_documents/test.md',
        './test_documents/test.html', 
        './test_documents/test.csv',
        './test_documents/test.json'
    ]
    
    print("🧪 Testing Enhanced File Format Support")
    print(f"{'='*60}")
    
    for file_path in test_files:
        if os.path.exists(file_path):
            await test_file_format(file_path)
        else:
            print(f"❌ File not found: {file_path}")
    
    print(f"\n{'='*60}")
    print("✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())