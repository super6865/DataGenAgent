"""
Document service for managing documents
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.document import Document
from app.core.config import settings
from app.services.document_parsing_task import DocumentParsingTask
import os
import logging
import asyncio
from datetime import datetime
from werkzeug.utils import secure_filename
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing documents"""
    
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.DOCUMENT_UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_allowed_file(self, filename: str) -> bool:
        """Check if file type is allowed"""
        if not filename:
            return False
        ext = Path(filename).suffix.lower()
        return ext in settings.ALLOWED_DOCUMENT_TYPES
    
    def _generate_safe_filename(self, original_filename: str) -> str:
        """Generate a safe filename with timestamp"""
        name, ext = os.path.splitext(original_filename)
        safe_name = secure_filename(name)
        if not safe_name:
            safe_name = "document"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{safe_name}{ext}"
    
    def upload_document(
        self,
        file_content: bytes,
        filename: str,
        file_size: int,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Upload a document file
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            file_size: File size in bytes
            created_by: User ID who uploaded the document
        
        Returns:
            Document information dict
        """
        try:
            # Validate file type
            if not self._is_allowed_file(filename):
                raise ValueError(f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_DOCUMENT_TYPES)}")
            
            # Validate file size
            if file_size > settings.MAX_DOCUMENT_SIZE:
                raise ValueError(f"File size exceeds maximum limit of {settings.MAX_DOCUMENT_SIZE / (1024*1024)}MB")
            
            # Check for duplicate document name
            existing_document = self.db.query(Document).filter(Document.name == filename).first()
            if existing_document:
                raise ValueError(f"文档名称 '{filename}' 已存在，请重命名后上传或删除已存在的文档")
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(filename)
            file_path = self.upload_dir / safe_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Get file type
            file_type = Path(filename).suffix.lower().lstrip('.')
            
            # Create document record
            document = Document(
                name=filename,
                file_path=str(file_path),
                file_type=file_type,
                file_size=file_size,
                upload_time=datetime.utcnow(),
                parse_status="pending",
                created_by=created_by
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Document uploaded successfully: {document.id} - {filename}")
            
            # Trigger asynchronous document parsing
            try:
                self._trigger_async_parsing(document.id)
            except Exception as e:
                logger.warning(f"Failed to trigger async parsing for document {document.id}: {str(e)}")
                # Don't fail the upload if parsing trigger fails
            
            return self._document_to_dict(document)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error uploading document: {str(e)}", exc_info=True)
            raise
    
    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return None
        return self._document_to_dict(document)
    
    def get_documents(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get documents list with pagination and search
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search keyword for document name
        
        Returns:
            Tuple of (documents list, total count)
        """
        try:
            query = self.db.query(Document)
            
            # Apply search filter
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        Document.name.like(search_pattern),
                        Document.file_type.like(search_pattern)
                    )
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            documents = query.order_by(Document.upload_time.desc()).offset(skip).limit(limit).all()
            
            result = [self._document_to_dict(doc) for doc in documents]
            
            return result, total
            
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}", exc_info=True)
            return [], 0
    
    def delete_document(self, document_id: int) -> bool:
        """
        Delete a document
        
        Args:
            document_id: Document ID to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return False
            
            # Delete file from filesystem
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Delete database record
            self.db.delete(document)
            self.db.commit()
            
            logger.info(f"Document deleted successfully: {document_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting document: {str(e)}", exc_info=True)
            return False
    
    def rename_document(self, document_id: int, new_name: str) -> Optional[Dict[str, Any]]:
        """
        Rename a document
        
        Args:
            document_id: Document ID to rename
            new_name: New document name
        
        Returns:
            Updated document information dict, or None if not found
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
            
            document.name = new_name
            document.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Document renamed successfully: {document_id} -> {new_name}")
            
            return self._document_to_dict(document)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error renaming document: {str(e)}", exc_info=True)
            raise
    
    def update_parse_status(
        self,
        document_id: int,
        status: str,
        parse_result: Optional[Dict[str, Any]] = None,
        document_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update document parse status
        
        Args:
            document_id: Document ID
            status: Parse status (pending, parsing, success, failed)
            parse_result: Parsed document content
            document_type: Document type (api, requirement, unknown)
        
        Returns:
            Updated document information dict, or None if not found
        """
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return None
            
            document.parse_status = status
            if parse_result is not None:
                document.parse_result = parse_result
            if document_type is not None:
                document.document_type = document_type
            document.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(document)
            
            return self._document_to_dict(document)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating parse status: {str(e)}", exc_info=True)
            raise
    
    def _trigger_async_parsing(self, document_id: int) -> None:
        """
        Trigger asynchronous document parsing with intent recognition
        
        This method is called when a document is uploaded.
        It performs both content parsing and intent recognition.
        If intent recognition fails, content parsing still succeeds.
        
        Args:
            document_id: Document ID to parse
        """
        try:
            # Use asyncio to run parsing in background
            # This is a fire-and-forget operation
            def run_parsing():
                """Run parsing with intent recognition in a separate thread"""
                try:
                    from app.core.database import SessionLocal
                    background_db = SessionLocal()
                    try:
                        parsing_task = DocumentParsingTask(background_db)
                        asyncio.run(parsing_task.parse_document_with_intent_async(document_id))
                    finally:
                        background_db.close()
                except Exception as e:
                    logger.error(f"Error in background parsing with intent: {str(e)}", exc_info=True)
            
            # Run in a separate thread to avoid blocking
            import threading
            thread = threading.Thread(target=run_parsing, daemon=True)
            thread.start()
            
            logger.info(f"Triggered async parsing with intent for document {document_id}")
            
        except Exception as e:
            logger.error(f"Error triggering async parsing with intent: {str(e)}", exc_info=True)
    
    def trigger_parsing(self, document_id: int, with_intent: bool = False) -> Dict[str, Any]:
        """
        Manually trigger document parsing (synchronous)
        
        Args:
            document_id: Document ID to parse
            with_intent: If True, also perform intent recognition. Default is False (content only)
        
        Returns:
            Parsing result dictionary
        """
        try:
            parsing_task = DocumentParsingTask(self.db)
            # Run synchronously using asyncio.run
            if with_intent:
                result = asyncio.run(parsing_task.parse_document_with_intent(document_id))
            else:
                result = asyncio.run(parsing_task.parse_document_content(document_id))
            return result
        except Exception as e:
            logger.error(f"Error in manual parsing trigger: {str(e)}", exc_info=True)
            raise
    
    def _document_to_dict(self, document: Document) -> Dict[str, Any]:
        """Convert document model to dict"""
        return {
            "id": document.id,
            "name": document.name,
            "file_path": document.file_path,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "upload_time": document.upload_time.isoformat() if document.upload_time else None,
            "parse_status": document.parse_status,
            "parse_result": document.parse_result,
            "document_type": document.document_type,
            "created_by": document.created_by,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        }
