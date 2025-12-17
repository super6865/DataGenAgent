"""
Document parser service for extracting and structuring document content
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json

# Document parsing libraries
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import markdown
except ImportError:
    markdown = None

from app.services.mcp_service import MCPService

logger = logging.getLogger(__name__)


class DocumentParserService:
    """Service for parsing documents and extracting structured content"""
    
    def __init__(self):
        """Initialize document parser service"""
        self.mcp_service = MCPService()
        self.use_mcp = self.mcp_service.is_available()
    
    async def parse_document(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Parse document and extract structured content
        
        Args:
            file_path: Path to the document file
            file_type: File type (md, docx, pdf, txt)
        
        Returns:
            Structured document content as JSON
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        try:
            # Try MCP parsing first if available
            if self.use_mcp:
                try:
                    logger.info(f"Attempting to parse document via MCP: {file_path}")
                    return await self.mcp_service.parse_document(file_path)
                except Exception as e:
                    logger.warning(f"MCP parsing failed, falling back to local parsing: {str(e)}")
            
            # Fall back to local parsing
            logger.info(f"Parsing document locally: {file_path}")
            raw_content = self._extract_raw_content(file_path, file_type)
            structured_content = self._structure_content(raw_content, file_type)
            
            return {
                "raw_content": raw_content,
                "structured_content": structured_content,
                "metadata": self._extract_metadata(raw_content, file_type)
            }
            
        except Exception as e:
            logger.error(f"Error parsing document: {str(e)}", exc_info=True)
            raise
    
    def _extract_raw_content(self, file_path: str, file_type: str) -> str:
        """Extract raw text content from document"""
        file_path_obj = Path(file_path)
        
        if file_type == "txt" or file_type == "md":
            # Text and Markdown files
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Try with different encoding
                with open(file_path_obj, 'r', encoding='gbk') as f:
                    return f.read()
        
        elif file_type == "docx":
            # Word documents
            if DocxDocument is None:
                raise ImportError("python-docx is not installed")
            
            doc = DocxDocument(file_path_obj)
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            return "\n".join(paragraphs)
        
        elif file_type == "pdf":
            # PDF documents
            if PyPDF2 is None:
                raise ImportError("PyPDF2 is not installed")
            
            text_content = []
            with open(file_path_obj, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
            return "\n".join(text_content)
        
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _structure_content(self, raw_content: str, file_type: str) -> Dict[str, Any]:
        """Structure the raw content into sections, tables, code blocks, etc."""
        structured = {
            "sections": [],
            "tables": [],
            "code_blocks": [],
            "lists": []
        }
        
        lines = raw_content.split('\n')
        current_section = None
        current_code_block = []
        in_code_block = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detect code blocks (for markdown)
            if file_type == "md":
                if line_stripped.startswith('```'):
                    if in_code_block:
                        # End of code block
                        if current_code_block:
                            structured["code_blocks"].append({
                                "content": "\n".join(current_code_block),
                                "line_start": i - len(current_code_block),
                                "line_end": i
                            })
                        current_code_block = []
                        in_code_block = False
                    else:
                        # Start of code block
                        in_code_block = True
                    continue
                
                if in_code_block:
                    current_code_block.append(line)
                    continue
            
            # Detect sections (headers)
            if file_type == "md" and line_stripped.startswith('#'):
                level = len(line_stripped) - len(line_stripped.lstrip('#'))
                title = line_stripped.lstrip('#').strip()
                if current_section:
                    structured["sections"].append(current_section)
                current_section = {
                    "level": level,
                    "title": title,
                    "content": [],
                    "line_start": i
                }
            elif current_section:
                current_section["content"].append(line)
            elif not current_section:
                # Content before any section
                if not structured.get("preamble"):
                    structured["preamble"] = []
                structured["preamble"].append(line)
        
        # Add last section
        if current_section:
            structured["sections"].append(current_section)
        
        return structured
    
    def _extract_metadata(self, raw_content: str, file_type: str) -> Dict[str, Any]:
        """Extract metadata from document content"""
        metadata = {
            "title": "",
            "keywords": [],
            "extracted_fields": [],
            "word_count": len(raw_content.split()),
            "line_count": len(raw_content.split('\n'))
        }
        
        # Try to extract title (first line or first header)
        lines = raw_content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line_stripped = line.strip()
            if line_stripped:
                if file_type == "md" and line_stripped.startswith('#'):
                    metadata["title"] = line_stripped.lstrip('#').strip()
                elif not metadata["title"]:
                    metadata["title"] = line_stripped[:100]  # First 100 chars
                break
        
        # Extract potential keywords (simple heuristic: capitalized words, common terms)
        words = raw_content.split()
        keywords = set()
        for word in words:
            if len(word) > 4 and word[0].isupper():
                keywords.add(word.lower())
        metadata["keywords"] = list(keywords)[:20]  # Top 20 keywords
        
        return metadata
