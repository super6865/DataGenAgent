"""
Generation history API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import time
from datetime import datetime
from app.core.database import get_db
from app.services.generation_history_service import GenerationHistoryService
from app.services.llm_service import DataGenerationAgent
from app.services.model_config_service import ModelConfigService
from app.services.observability_service import ObservabilityService
from app.utils.api_decorators import handle_api_errors, handle_not_found

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=Dict[str, Any])
@handle_api_errors
async def get_history_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get list of generation history with pagination"""
    try:
        service = GenerationHistoryService(db)
        histories, total = service.get_history_list(skip=skip, limit=limit)
        return {
            "success": True,
            "data": histories or [],
            "total": total or 0,
            "message": "Get history list successfully"
        }
    except Exception as e:
        logger.error(f"Error getting history list: {str(e)}", exc_info=True)
        raise


@router.get("/{history_id}", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("History not found")
async def get_history_by_id(
    history_id: int,
    db: Session = Depends(get_db)
):
    """Get generation history by ID"""
    service = GenerationHistoryService(db)
    history = service.get_history_by_id(history_id)
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    return {
        "success": True,
        "data": history,
        "message": "Get history successfully"
    }


@router.delete("/{history_id}", response_model=Dict[str, Any])
@handle_api_errors
async def delete_history(
    history_id: int,
    db: Session = Depends(get_db)
):
    """Delete generation history"""
    service = GenerationHistoryService(db)
    result = service.delete_history(history_id)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to delete history')
        )
    
    return result


@router.post("/{history_id}/regenerate", response_model=Dict[str, Any])
@handle_api_errors
async def regenerate_history(
    history_id: int,
    db: Session = Depends(get_db)
):
    """Regenerate data from history"""
    trace_start_time = time.time()
    trace_id = None
    observability_service = ObservabilityService(db)
    
    try:
        # Create trace for observability
        trace_result = observability_service.create_trace(
            service_name="data-generation",
            operation_name="regenerate_history",
            attributes={
                "history_id": history_id
            }
        )
        if trace_result.get('success'):
            trace_id = trace_result['data']['trace_id']
            logger.info(f"Created trace for regenerate_history: {trace_id}")
        else:
            logger.warning(f"Failed to create trace: {trace_result.get('message')}")
    
    except Exception as e:
        logger.warning(f"Failed to create trace for regenerate_history: {str(e)}")
        # Continue without trace
    
    history_service = GenerationHistoryService(db)
    history = history_service.get_history_by_id(history_id)
    
    if not history:
        if trace_id:
            trace_duration = (time.time() - trace_start_time) * 1000
            observability_service.update_trace(
                trace_id=trace_id,
                end_time=datetime.utcnow(),
                duration_ms=trace_duration,
                status_code="ERROR",
                status_message="History not found"
            )
        raise HTTPException(status_code=404, detail="History not found")
    
    # Get model configuration
    model_config_service = ModelConfigService(db)
    model_config_id = history.get('model_config_id')
    
    if model_config_id:
        model_config_dict = model_config_service.get_config_dict_for_llm(model_config_id)
        if not model_config_dict:
            if trace_id:
                trace_duration = (time.time() - trace_start_time) * 1000
                observability_service.update_trace(
                    trace_id=trace_id,
                    end_time=datetime.utcnow(),
                    duration_ms=trace_duration,
                    status_code="ERROR",
                    status_message="Model configuration not found"
                )
            raise HTTPException(status_code=404, detail="Model configuration not found")
    else:
        # Use default model config
        default_config = model_config_service.get_default_config(include_sensitive=True)
        if not default_config:
            if trace_id:
                trace_duration = (time.time() - trace_start_time) * 1000
                observability_service.update_trace(
                    trace_id=trace_id,
                    end_time=datetime.utcnow(),
                    duration_ms=trace_duration,
                    status_code="ERROR",
                    status_message="No model configuration found"
                )
            raise HTTPException(
                status_code=400, 
                detail="No model configuration found. Please configure a model first."
            )
        model_config_dict = model_config_service.get_config_dict_for_llm(default_config['id'])
    
    # Create agent and regenerate
    from app.services.data_parser import DataParser
    from app.services.format_converter import FormatConverter
    
    try:
        agent = DataGenerationAgent(model_config_dict)
        generated_content, usage = await agent.generate_data(
            user_query=history['user_query'],
            format_hint=history['data_format'],
            trace_id=trace_id,
            observability_service=observability_service
        )
    except Exception as e:
        # Update trace with error
        if trace_id:
            trace_duration = (time.time() - trace_start_time) * 1000
            observability_service.update_trace(
                trace_id=trace_id,
                end_time=datetime.utcnow(),
                duration_ms=trace_duration,
                status_code="ERROR",
                status_message=str(e)
            )
        raise
    
    # Parse and format
    parsed_data = DataParser.parse_generated_data(
        content=generated_content,
        format=history['data_format']
    )
    
    final_format = history['data_format']
    if final_format == "json":
        formatted_data = FormatConverter.convert_to_json(parsed_data)
    elif final_format == "csv":
        if isinstance(parsed_data, list):
            formatted_data = FormatConverter.convert_to_csv(parsed_data)
        else:
            formatted_data = generated_content
    elif final_format == "excel":
        if isinstance(parsed_data, list):
            excel_bytes = FormatConverter.convert_to_excel(parsed_data)
            import base64
            formatted_data = base64.b64encode(excel_bytes).decode('utf-8')
        else:
            formatted_data = generated_content
    else:
        formatted_data = str(parsed_data) if not isinstance(parsed_data, str) else parsed_data
    
    # Create new history entry
    model_name = f"{model_config_dict.get('model_type', 'unknown')}/{model_config_dict.get('model_version', 'unknown')}"
    history_result = history_service.create_history(
        user_query=history['user_query'],
        generated_data=formatted_data,
        data_format=final_format,
        model_used=model_name,
        model_config_id=model_config_id
    )
    
    # Update trace with success
    if trace_id:
        trace_duration = (time.time() - trace_start_time) * 1000
        observability_service.update_trace(
            trace_id=trace_id,
            end_time=datetime.utcnow(),
            duration_ms=trace_duration,
            status_code="OK",
            attributes={
                "user_query": history['user_query'],
                "format": final_format,
                "model_config_id": model_config_id,
                "usage": usage,
                "history_id": history_id,
                "new_history_id": history_result.get('data', {}).get('id') if history_result.get('success') else None
            }
        )
    
    return {
        "success": True,
        "data": {
            "generated_data": formatted_data,
            "format": final_format,
            "usage": usage,
            "history_id": history_result.get('data', {}).get('id') if history_result.get('success') else None,
        },
        "message": "Data regenerated successfully"
    }
