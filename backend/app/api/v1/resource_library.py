"""
Resource library API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from sqlalchemy import func
from app.core.database import get_db
from app.models.document import Document
from app.utils.api_decorators import handle_api_errors
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=Dict[str, Any])
@handle_api_errors
async def get_resource_library_stats(
    db: Session = Depends(get_db)
):
    """
    Get resource library statistics
    
    Args:
        db: Database session
    
    Returns:
        Statistics including document count and datasource count
    """
    try:
        # Count documents
        documents_count = db.query(func.count(Document.id)).scalar() or 0
        
        # Datasources count (placeholder for future implementation)
        datasources_count = 0
        
        return {
            "success": True,
            "data": {
                "documents_count": documents_count,
                "datasources_count": datasources_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting resource library stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
