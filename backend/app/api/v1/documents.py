"""
Document management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from app.core.database import get_db
from app.services.document_service import DocumentService
from app.utils.api_decorators import handle_api_errors
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentRenameRequest(BaseModel):
    name: str


@router.post("/upload", response_model=Dict[str, Any])
@handle_api_errors
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document file
    
    Args:
        file: Uploaded file
        db: Database session
    
    Returns:
        Document information
    """
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        filename = file.filename or "unknown"
        
        # Create document service
        document_service = DocumentService(db)
        
        # Upload document
        document = document_service.upload_document(
            file_content=file_content,
            filename=filename,
            file_size=file_size,
            created_by=None  # TODO: Get from authentication
        )
        
        return {
            "success": True,
            "data": document,
            "message": "Document uploaded successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.get("", response_model=Dict[str, Any])
@handle_api_errors
async def get_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search keyword"),
    db: Session = Depends(get_db)
):
    """
    Get documents list with pagination and search
    
    Args:
        page: Page number (starts from 1)
        page_size: Number of items per page
        search: Search keyword
        db: Database session
    
    Returns:
        Documents list with pagination info
    """
    try:
        document_service = DocumentService(db)
        
        skip = (page - 1) * page_size
        documents, total = document_service.get_documents(
            skip=skip,
            limit=page_size,
            search=search
        )
        
        return {
            "success": True,
            "data": {
                "items": documents,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")


@router.get("/{document_id}", response_model=Dict[str, Any])
@handle_api_errors
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document by ID
    
    Args:
        document_id: Document ID
        db: Database session
    
    Returns:
        Document information
    """
    try:
        document_service = DocumentService(db)
        document = document_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "data": document
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.delete("/{document_id}", response_model=Dict[str, Any])
@handle_api_errors
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a document
    
    Args:
        document_id: Document ID to delete
        db: Database session
    
    Returns:
        Success status
    """
    try:
        document_service = DocumentService(db)
        success = document_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.put("/{document_id}/rename", response_model=Dict[str, Any])
@handle_api_errors
async def rename_document(
    document_id: int,
    request: DocumentRenameRequest,
    db: Session = Depends(get_db)
):
    """
    Rename a document
    
    Args:
        document_id: Document ID to rename
        request: Rename request with new name
        db: Database session
    
    Returns:
        Updated document information
    """
    try:
        document_service = DocumentService(db)
        document = document_service.rename_document(document_id, request.name)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "data": document,
            "message": "Document renamed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rename document: {str(e)}")


@router.post("/{document_id}/parse", response_model=Dict[str, Any])
@handle_api_errors
async def parse_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger document content parsing (without intent recognition)
    
    This endpoint only parses the document content, extracting text and structure.
    It does not perform intent recognition (document type classification).
    
    Args:
        document_id: Document ID to parse
        db: Database session
    
    Returns:
        Parsing result
    """
    try:
        document_service = DocumentService(db)
        
        # Check if document exists
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Trigger content parsing only (without intent recognition)
        result = document_service.trigger_parsing(document_id, with_intent=False)
        
        return {
            "success": result.get("success", True),
            "data": {
                "document_id": document_id,
                "parse_status": "success" if result.get("success") else "failed",
                "document_type": result.get("document_type"),
                "parse_result": result.get("parse_result")
            },
            "message": "Document content parsing completed" if result.get("success") else "Document content parsing failed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse document: {str(e)}")


@router.get("/{document_id}/parse-status", response_model=Dict[str, Any])
@handle_api_errors
async def get_parse_status(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document parsing status
    
    Args:
        document_id: Document ID
        db: Database session
    
    Returns:
        Parsing status information
    """
    try:
        document_service = DocumentService(db)
        document = document_service.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "data": {
                "document_id": document_id,
                "parse_status": document.get("parse_status"),
                "document_type": document.get("document_type"),
                "has_parse_result": document.get("parse_result") is not None,
                "parse_result_summary": _get_parse_result_summary(document.get("parse_result"))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parse status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get parse status: {str(e)}")


@router.post("/{document_id}/parse-with-intent", response_model=Dict[str, Any])
@handle_api_errors
async def parse_document_with_intent(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger document parsing with intent recognition
    
    This endpoint parses the document content and also performs intent recognition
    to classify the document type (API document vs Requirement document).
    This requires a model configuration to be set up.
    
    Args:
        document_id: Document ID to parse
        db: Database session
    
    Returns:
        Parsing result with intent recognition
    """
    try:
        document_service = DocumentService(db)
        
        # Check if document exists
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Trigger parsing with intent recognition
        result = document_service.trigger_parsing(document_id, with_intent=True)
        
        return {
            "success": result.get("success", True),
            "data": {
                "document_id": document_id,
                "parse_status": "success" if result.get("success") else "failed",
                "document_type": result.get("document_type"),
                "parse_result": result.get("parse_result")
            },
            "message": "Document parsing with intent recognition completed" if result.get("success") else "Document parsing with intent recognition failed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing document with intent: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse document with intent: {str(e)}")


def _get_parse_result_summary(parse_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Get summary of parse result (without full content)
    
    Args:
        parse_result: Full parse result dictionary
    
    Returns:
        Summary dictionary
    """
    if not parse_result:
        return None
    
    summary = {}
    
    # Extract metadata
    if "metadata" in parse_result:
        metadata = parse_result["metadata"]
        summary["metadata"] = {
            "title": metadata.get("title"),
            "word_count": metadata.get("word_count"),
            "line_count": metadata.get("line_count"),
            "keywords_count": len(metadata.get("keywords", []))
        }
    
    # Extract structured content summary
    if "structured_content" in parse_result:
        structured = parse_result["structured_content"]
        summary["structured_content"] = {
            "sections_count": len(structured.get("sections", [])),
            "tables_count": len(structured.get("tables", [])),
            "code_blocks_count": len(structured.get("code_blocks", [])),
            "lists_count": len(structured.get("lists", []))
        }
    
    # Extract intent recognition result
    if "intent_recognition" in parse_result:
        intent = parse_result["intent_recognition"]
        summary["intent_recognition"] = {
            "document_type": intent.get("document_type"),
            "confidence": intent.get("confidence"),
            "reasoning": intent.get("reasoning", "")[:200]  # First 200 chars
        }
    
    return summary
