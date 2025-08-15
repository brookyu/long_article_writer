"""
Text processing and chunking service for document analysis
"""

import re
import hashlib
from typing import List, Tuple, Optional
from pathlib import Path
import asyncio
import logging

# Document parsers
import PyPDF2
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)


class TextChunk:
    """Represents a chunk of text with metadata"""
    
    def __init__(self, text: str, chunk_index: int, char_count: int, start_pos: int = 0, end_pos: int = 0):
        self.text = text.strip()
        self.chunk_index = chunk_index
        self.char_count = char_count
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.hash = hashlib.md5(self.text.encode()).hexdigest()


class DocumentProcessor:
    """Handles document parsing and text chunking"""
    
    def __init__(self, max_chunk_size: int = 1000, overlap_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
    
    async def extract_text_from_file(self, file_path: str, mime_type: str) -> str:
        """Extract text content from various file formats"""
        try:
            if mime_type == "text/plain":
                return await self._extract_from_txt(file_path)
            elif mime_type == "application/pdf":
                return await self._extract_from_pdf(file_path)
            elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                             "application/msword"]:
                return await self._extract_from_docx(file_path)
            else:
                # Fallback: try to read as text
                return await self._extract_from_txt(file_path)
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise
    
    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"Could not decode text file: {file_path}")
    
    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF files"""
        text_content = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
        
        return "\n\n".join(text_content)
    
    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        doc = DocxDocument(file_path)
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)
        
        return "\n\n".join(paragraphs)
    
    def create_chunks(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks for better context preservation"""
        if not text.strip():
            return []
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Split into sentences for better chunk boundaries
        sentences = self._split_into_sentences(cleaned_text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for i, sentence in enumerate(sentences):
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                # Create chunk from current content
                chunk = TextChunk(
                    text=current_chunk.strip(),
                    chunk_index=chunk_index,
                    char_count=len(current_chunk.strip()),
                    start_pos=current_start,
                    end_pos=current_start + len(current_chunk)
                )
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, self.overlap_size)
                current_chunk = overlap_text + sentence
                current_start = current_start + len(current_chunk) - len(overlap_text)
            else:
                current_chunk += sentence
        
        # Add final chunk if there's remaining content
        if current_chunk.strip():
            chunk = TextChunk(
                text=current_chunk.strip(),
                chunk_index=chunk_index,
                char_count=len(current_chunk.strip()),
                start_pos=current_start,
                end_pos=current_start + len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page breaks and form feeds
        text = re.sub(r'[\f\r]+', '\n', text)
        
        # Normalize line breaks
        text = re.sub(r'\n+', '\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunk boundaries"""
        # Simple sentence splitting - can be enhanced with spaCy or NLTK
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out very short segments
        sentences = [s.strip() + ' ' for s in sentences if len(s.strip()) > 10]
        
        return sentences
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get the last N characters for overlap"""
        if len(text) <= overlap_size:
            return text
        
        # Try to break at word boundaries
        overlap_text = text[-overlap_size:]
        space_index = overlap_text.find(' ')
        
        if space_index > 0:
            return overlap_text[space_index:] + " "
        
        return overlap_text + " "


class DocumentAnalyzer:
    """High-level document analysis orchestrator"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
    
    async def analyze_document(self, file_path: str, mime_type: str) -> Tuple[str, List[TextChunk]]:
        """
        Analyze a document and return extracted text and chunks
        
        Returns:
            Tuple of (full_text, text_chunks)
        """
        try:
            # Extract text content
            logger.info(f"Extracting text from {file_path}")
            full_text = await self.processor.extract_text_from_file(file_path, mime_type)
            
            if not full_text.strip():
                raise ValueError("No text content found in document")
            
            # Create chunks
            logger.info(f"Creating chunks for document with {len(full_text)} characters")
            chunks = self.processor.create_chunks(full_text)
            
            logger.info(f"Created {len(chunks)} chunks from document")
            
            return full_text, chunks
            
        except Exception as e:
            logger.error(f"Document analysis failed for {file_path}: {e}")
            raise


# Global analyzer instance
document_analyzer = DocumentAnalyzer()