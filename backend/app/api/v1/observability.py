"""
Observability API endpoints for trace and span management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import urllib.parse
from app.core.database import get_db
from app.services.observability_service import ObservabilityService
from app.utils.api_decorators import handle_api_errors, handle_not_found

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/traces", response_model=Dict[str, Any])
@handle_api_errors
async def list_traces(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of traces with pagination and filters"""
    try:
        service = ObservabilityService(db)
        
        # Parse datetime strings
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                start_dt = datetime.fromisoformat(start_time)
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except:
                end_dt = datetime.fromisoformat(end_time)
        
        traces, total = service.get_trace_list(
            skip=skip,
            limit=limit,
            service_name=service_name,
            start_time=start_dt,
            end_time=end_dt
        )
        
        return {
            "success": True,
            "traces": traces or [],
            "total": total or 0,
            "message": "Get traces successfully"
        }
    except Exception as e:
        logger.error(f"Error getting traces: {str(e)}", exc_info=True)
        raise


@router.get("/traces/{trace_id}", response_model=Dict[str, Any])
@handle_api_errors
async def get_trace(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """Get trace by trace_id"""
    try:
        service = ObservabilityService(db)
        trace = service.get_trace_by_id(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {
            "success": True,
            "trace": trace,
            "message": "Get trace successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace: {str(e)}", exc_info=True)
        raise


@router.get("/traces/{trace_id}/detail", response_model=Dict[str, Any])
@handle_api_errors
async def get_trace_detail(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """Get trace detail with all spans"""
    try:
        # URL 解码（FastAPI 应该自动处理，但确保正确）
        trace_id = urllib.parse.unquote(trace_id)
        
        logger.info(f"Getting trace detail for trace_id: {trace_id} (length: {len(trace_id)})")
        service = ObservabilityService(db)
        detail = service.get_trace_detail(trace_id)
        if not detail:
            logger.warning(f"Trace not found: {trace_id}")
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        logger.info(f"Successfully retrieved trace detail for trace_id: {trace_id}")
        return {
            "success": True,
            **detail,
            "message": "Get trace detail successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace detail: {str(e)}", exc_info=True)
        raise


@router.get("/traces/{trace_id}/spans", response_model=Dict[str, Any])
@handle_api_errors
async def list_spans(
    trace_id: str,
    db: Session = Depends(get_db)
):
    """Get all spans for a trace"""
    try:
        service = ObservabilityService(db)
        spans = service.get_spans_by_trace_id(trace_id)
        return {
            "success": True,
            "spans": spans or [],
            "message": "Get spans successfully"
        }
    except Exception as e:
        logger.error(f"Error getting spans: {str(e)}", exc_info=True)
        raise
