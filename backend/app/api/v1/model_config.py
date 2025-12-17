"""
Model configuration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging
from app.core.database import get_db
from app.services.model_config_service import ModelConfigService
from app.utils.api_decorators import handle_api_errors, handle_not_found

logger = logging.getLogger(__name__)
router = APIRouter()


class ModelConfigCreate(BaseModel):
    config_name: str
    model_type: str
    model_version: str
    api_key: str
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = 120
    is_enabled: Optional[bool] = True
    is_default: Optional[bool] = False


class ModelConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None


@router.get("", response_model=Dict[str, Any])
@handle_api_errors
async def get_all_configs(
    include_sensitive: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all model configurations with pagination"""
    try:
        service = ModelConfigService(db)
        configs, total = service.get_all_configs(include_sensitive=include_sensitive, skip=skip, limit=limit)
        return {
            "success": True,
            "data": configs or [],
            "total": total or 0,
            "message": "Get configurations successfully"
        }
    except Exception as e:
        logger.error(f"Error getting configs: {str(e)}", exc_info=True)
        raise


@router.get("/{config_id}", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Configuration not found")
async def get_config_by_id(
    config_id: int,
    include_sensitive: bool = False,
    db: Session = Depends(get_db)
):
    """Get model configuration by ID"""
    service = ModelConfigService(db)
    config = service.get_config_by_id(config_id, include_sensitive=include_sensitive)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {
        "success": True,
        "data": config,
        "message": "Get configuration successfully"
    }


@router.get("/default/config", response_model=Dict[str, Any])
@handle_api_errors
async def get_default_config(
    include_sensitive: bool = False,
    db: Session = Depends(get_db)
):
    """Get default model configuration"""
    service = ModelConfigService(db)
    config = service.get_default_config(include_sensitive=include_sensitive)
    if not config:
        return {
            "success": False,
            "data": None,
            "message": "No default configuration found"
        }
    return {
        "success": True,
        "data": config,
        "message": "Get default configuration successfully"
    }


@router.post("", response_model=Dict[str, Any])
@handle_api_errors
async def create_config(
    data: ModelConfigCreate,
    db: Session = Depends(get_db)
):
    """Create a new model configuration"""
    service = ModelConfigService(db)
    result = service.create_config(data.dict())
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to create configuration')
        )
    
    return result


@router.put("/{config_id}", response_model=Dict[str, Any])
@handle_api_errors
async def update_config(
    config_id: int,
    data: ModelConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update model configuration"""
    service = ModelConfigService(db)
    result = service.update_config(config_id, data.dict(exclude_unset=True))
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to update configuration')
        )
    
    return result


@router.delete("/{config_id}", response_model=Dict[str, Any])
@handle_api_errors
async def delete_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Delete model configuration"""
    service = ModelConfigService(db)
    result = service.delete_config(config_id)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to delete configuration')
        )
    
    return result


@router.put("/{config_id}/set-default", response_model=Dict[str, Any])
@handle_api_errors
async def set_default_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Set model configuration as default"""
    service = ModelConfigService(db)
    result = service.update_config(config_id, {'is_default': True})
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to set default configuration')
        )
    
    return result
