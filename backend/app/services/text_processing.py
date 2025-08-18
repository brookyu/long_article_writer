"""
Text processing and chunking service for document analysis
"""

import re
import hashlib
import json
import csv
from typing import List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import logging
import magic
import chardet
import aiofiles

# Document parsers
import PyPDF2
from docx import Document as DocxDocument
import mammoth
import docx2txt
import markdown
from bs4 import BeautifulSoup
from striprtf.striprtf import rtf_to_text

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
        self.supported_formats = {
            'text/plain': self._extract_from_txt,
            'text/markdown': self._extract_from_markdown,
            'text/html': self._extract_from_html,
            'application/pdf': self._extract_from_pdf,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._extract_from_docx,
            'application/msword': self._extract_from_doc,  # Use separate handler for .doc files
            'application/rtf': self._extract_from_rtf,
            'text/rtf': self._extract_from_rtf,
            'text/csv': self._extract_from_csv,
            'application/json': self._extract_from_json,
            'text/json': self._extract_from_json,
            'audio/wav': self._extract_from_audio,
            'audio/mpeg': self._extract_from_audio,
            'audio/mp3': self._extract_from_audio,
            'audio/mp4': self._extract_from_audio,
            'audio/flac': self._extract_from_audio,
            'audio/ogg': self._extract_from_audio,
            'audio/aac': self._extract_from_audio,
        }
    
    async def detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type using multiple methods"""
        try:
            # First try python-magic for accurate detection
            mime_type = magic.from_file(file_path, mime=True)
            logger.info(f"Detected MIME type for {file_path}: {mime_type}")
            
            # Override magic detection for common extensions that might be misdetected
            file_ext = Path(file_path).suffix.lower()
            extension_overrides = {
                '.md': 'text/markdown',
                '.markdown': 'text/markdown',
                '.wav': 'audio/wav',
                '.mp3': 'audio/mp3',
                '.m4a': 'audio/mp4',
                '.flac': 'audio/flac',
                '.ogg': 'audio/ogg',
                '.aac': 'audio/aac',
                '.csv': 'text/csv',
                '.json': 'application/json',
            }
            
            if file_ext in extension_overrides:
                corrected_type = extension_overrides[file_ext]
                logger.info(f"Overriding MIME type for {file_path} from {mime_type} to {corrected_type}")
                return corrected_type
                
            return mime_type
        except Exception as e:
            logger.warning(f"Failed to detect MIME type with magic: {e}")
            
            # Fallback to file extension
            file_ext = Path(file_path).suffix.lower()
            extension_map = {
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.markdown': 'text/markdown',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.rtf': 'application/rtf',
                '.csv': 'text/csv',
                '.json': 'application/json',
            }
            
            mime_type = extension_map.get(file_ext, 'text/plain')
            logger.info(f"Using extension-based MIME type for {file_path}: {mime_type}")
            return mime_type
    
    async def extract_text_from_file(self, file_path: str, mime_type: Optional[str] = None) -> str:
        """Extract text content from various file formats"""
        try:
            # Auto-detect MIME type if not provided
            if not mime_type:
                mime_type = await self.detect_mime_type(file_path)
            
            # Get the appropriate extraction method
            extract_method = self.supported_formats.get(mime_type)
            
            if extract_method:
                logger.info(f"Extracting text from {file_path} using {extract_method.__name__}")
                return await extract_method(file_path)
            else:
                logger.warning(f"Unsupported MIME type {mime_type} for {file_path}, trying as text")
                return await self._extract_from_txt(file_path)
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise
    
    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from plain text files with smart encoding detection"""
        try:
            # First try to detect encoding
            async with aiofiles.open(file_path, 'rb') as file:
                raw_data = await file.read()
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8')
                confidence = detected.get('confidence', 0)
                
                logger.info(f"Detected encoding for {file_path}: {encoding} (confidence: {confidence:.2f})")
            
            # Use detected encoding if confidence is high enough
            if confidence > 0.7:
                async with aiofiles.open(file_path, 'r', encoding=encoding) as file:
                    return await file.read()
            
            # Fallback to common encodings
            for enc in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=enc) as file:
                        content = await file.read()
                        logger.info(f"Successfully read {file_path} with {enc} encoding")
                        return content
                except UnicodeDecodeError:
                    continue
                    
            raise ValueError(f"Could not decode text file with any encoding: {file_path}")
            
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            raise
    
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
        """Extract text from DOCX files using multiple methods"""
        try:
            # Try mammoth first (better formatting preservation)
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                if result.value.strip():
                    return result.value
        except Exception as e:
            logger.warning(f"Mammoth extraction failed for {file_path}: {e}")
        
        try:
            # Fallback to docx2txt
            text = docx2txt.process(file_path)
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"docx2txt extraction failed for {file_path}: {e}")
        
        try:
            # Final fallback to python-docx
            doc = DocxDocument(file_path)
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"All DOCX extraction methods failed for {file_path}: {e}")
            raise
    
    async def _extract_from_doc(self, file_path: str) -> str:
        """Extract text from legacy DOC files"""
        try:
            # Use docx2txt which supports both .doc and .docx
            text = docx2txt.process(file_path)
            if text.strip():
                return text
            else:
                raise ValueError("No text content extracted from DOC file")
        except Exception as e:
            logger.error(f"DOC extraction failed for {file_path}: {e}")
            # If docx2txt fails, suggest alternative approaches
            raise ValueError(f"Failed to extract text from DOC file: {e}. Consider converting to DOCX format.")
    
    async def _extract_from_markdown(self, file_path: str) -> str:
        """Extract text from Markdown files"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                md_content = await file.read()
            
            # Convert markdown to HTML first, then extract text
            html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract text while preserving some structure
            text_content = []
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'code', 'pre']):
                if element.name.startswith('h'):
                    # Add header with emphasis
                    text_content.append(f"\n\n## {element.get_text().strip()} ##\n")
                elif element.name in ['code', 'pre']:
                    # Preserve code blocks
                    text_content.append(f"\n```\n{element.get_text().strip()}\n```\n")
                else:
                    text_content.append(element.get_text().strip())
            
            return "\n".join(filter(None, text_content))
            
        except Exception as e:
            logger.error(f"Error reading markdown file {file_path}: {e}")
            # Fallback to plain text
            return await self._extract_from_txt(file_path)
    
    async def _extract_from_html(self, file_path: str) -> str:
        """Extract text from HTML files"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                html_content = await file.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Error reading HTML file {file_path}: {e}")
            # Fallback to plain text
            return await self._extract_from_txt(file_path)
    
    async def _extract_from_rtf(self, file_path: str) -> str:
        """Extract text from RTF files"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                rtf_content = await file.read()
            
            # Convert RTF to plain text
            text = rtf_to_text(rtf_content)
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error reading RTF file {file_path}: {e}")
            # Fallback to plain text
            return await self._extract_from_txt(file_path)
    
    async def _extract_from_csv(self, file_path: str) -> str:
        """Extract text from CSV files"""
        try:
            text_content = []
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
            
            # Parse CSV
            csv_reader = csv.reader(content.splitlines())
            rows = list(csv_reader)
            
            if not rows:
                return ""
            
            # Add header if exists
            headers = rows[0]
            text_content.append(f"CSV Data with columns: {', '.join(headers)}\n")
            
            # Add data rows (limit to avoid huge text)
            max_rows = min(100, len(rows))
            for i, row in enumerate(rows[:max_rows], 1):
                if i == 1:  # Skip header row in data
                    continue
                row_text = " | ".join(str(cell) for cell in row)
                text_content.append(f"Row {i-1}: {row_text}")
            
            if len(rows) > max_rows:
                text_content.append(f"\n... and {len(rows) - max_rows} more rows")
            
            return "\n".join(text_content)
            
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            # Fallback to plain text
            return await self._extract_from_txt(file_path)
    
    async def _extract_from_json(self, file_path: str) -> str:
        """Extract text from JSON files"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                json_content = await file.read()
            
            # Parse JSON
            data = json.loads(json_content)
            
            # Convert JSON to readable text
            def json_to_text(obj, prefix=""):
                if isinstance(obj, dict):
                    items = []
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            items.append(f"{prefix}{key}:")
                            items.append(json_to_text(value, prefix + "  "))
                        else:
                            items.append(f"{prefix}{key}: {value}")
                    return "\n".join(items)
                elif isinstance(obj, list):
                    items = []
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            items.append(f"{prefix}Item {i+1}:")
                            items.append(json_to_text(item, prefix + "  "))
                        else:
                            items.append(f"{prefix}Item {i+1}: {item}")
                    return "\n".join(items)
                else:
                    return str(obj)
            
            text = json_to_text(data)
            return f"JSON Data:\n{text}"
            
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            # Fallback to plain text
            return await self._extract_from_txt(file_path)
    
    async def _extract_from_audio(self, file_path: str) -> str:
        """Extract metadata from audio files"""
        try:
            file_path_obj = Path(file_path)
            file_size = file_path_obj.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            # Basic audio file metadata
            metadata_text = f"""Audio File: {file_path_obj.name}
File Type: {file_path_obj.suffix.upper()[1:]} Audio
File Size: {file_size_mb:.1f} MB
Date Modified: {datetime.fromtimestamp(file_path_obj.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}

This is an audio file. Audio content transcription is not yet supported, but the file has been indexed for organizational purposes.
You may want to add manual notes or transcription for this audio content.
"""
            
            logger.info(f"Processed audio file metadata for: {file_path}")
            return metadata_text
            
        except Exception as e:
            logger.error(f"Error processing audio file {file_path}: {e}")
            return f"Audio file: {Path(file_path).name} (Processing error: {str(e)})"
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return [
            '.txt', '.md', '.markdown', '.html', '.htm', 
            '.pdf', '.docx', '.doc', '.rtf', '.csv', '.json',
            '.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'
        ]
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file format is supported"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.get_supported_extensions()
    
    async def validate_file(self, file_path: str, max_size_mb: int = 10) -> dict:
        """Validate file before processing"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            file_path_obj = Path(file_path)
            
            # Check if file exists
            if not file_path_obj.exists():
                validation_result['valid'] = False
                validation_result['errors'].append(f"File does not exist: {file_path}")
                return validation_result
            
            # Check file size
            file_size = file_path_obj.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            validation_result['file_info']['size_mb'] = round(file_size_mb, 2)
            
            if file_size_mb > max_size_mb:
                validation_result['valid'] = False
                validation_result['errors'].append(f"File too large: {file_size_mb:.1f}MB (max: {max_size_mb}MB)")
            
            # Check file extension
            file_ext = file_path_obj.suffix.lower()
            validation_result['file_info']['extension'] = file_ext
            
            if not self.is_supported_file(file_path):
                validation_result['warnings'].append(f"Unsupported file format: {file_ext}")
            
            # Detect MIME type
            mime_type = await self.detect_mime_type(file_path)
            validation_result['file_info']['mime_type'] = mime_type
            
            # Check if file is readable
            try:
                async with aiofiles.open(file_path, 'rb') as f:
                    await f.read(1024)  # Try to read first 1KB
            except Exception as e:
                validation_result['valid'] = False
                validation_result['errors'].append(f"File not readable: {str(e)}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
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
    
    async def analyze_document(self, file_path: str, mime_type: Optional[str] = None) -> Tuple[str, List[TextChunk]]:
        """
        Analyze a document and return extracted text and chunks
        
        Returns:
            Tuple of (full_text, text_chunks)
        """
        try:
            # Validate file first
            logger.info(f"Validating file {file_path}")
            validation = await self.processor.validate_file(file_path)
            
            if not validation['valid']:
                error_msg = f"File validation failed: {', '.join(validation['errors'])}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if validation['warnings']:
                for warning in validation['warnings']:
                    logger.warning(warning)
            
            # Log file info
            file_info = validation['file_info']
            logger.info(f"Processing file: {file_info.get('size_mb', 0):.2f}MB, "
                       f"type: {file_info.get('mime_type', 'unknown')}")
            
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