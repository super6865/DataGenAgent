"""
Data template management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.services.data_template_service import DataTemplateService
from app.services.json_parser_service import JsonParserService
from app.agents.field_parser_agent import FieldParserAgent
from app.utils.api_decorators import handle_api_errors
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Template name")
    description: Optional[str] = Field(None, max_length=200, description="Template description")
    schema: Dict[str, Any] = Field(..., description="JSON Schema structure")
    field_definitions: list = Field(..., description="Field definitions list")
    example_data: Optional[Dict[str, Any]] = Field(None, description="Example data")


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Template name")
    description: Optional[str] = Field(None, max_length=200, description="Template description")
    schema: Optional[Dict[str, Any]] = Field(None, description="JSON Schema structure")
    field_definitions: Optional[list] = Field(None, description="Field definitions list")
    example_data: Optional[Dict[str, Any]] = Field(None, description="Example data")


class TemplateCopyRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="New template name")


class ParseJsonRequest(BaseModel):
    json_string: str = Field(..., description="JSON string to parse")
    use_agent: bool = Field(False, description="Whether to use AI agent for intelligent parsing")


@router.post("", response_model=Dict[str, Any])
@handle_api_errors
async def create_template(
    request: TemplateCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new data template
    
    Args:
        request: Template creation request
        db: Database session
    
    Returns:
        Created template information
    """
    try:
        template_service = DataTemplateService(db)
        
        template = template_service.create_template(
            name=request.name,
            description=request.description,
            schema=request.schema,
            field_definitions=request.field_definitions,
            example_data=request.example_data,
            created_by=None  # TODO: Get from authentication
        )
        
        return {
            "success": True,
            "data": template,
            "message": "Template created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.get("", response_model=Dict[str, Any])
@handle_api_errors
async def get_templates(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search keyword"),
    db: Session = Depends(get_db)
):
    """
    Get templates list with pagination and search
    
    Args:
        page: Page number (starts from 1)
        page_size: Number of items per page
        search: Search keyword
        db: Database session
    
    Returns:
        Templates list with pagination info
    """
    try:
        template_service = DataTemplateService(db)
        
        skip = (page - 1) * page_size
        templates, total = template_service.get_templates(
            skip=skip,
            limit=page_size,
            search=search
        )
        
        return {
            "success": True,
            "data": {
                "items": templates,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")


@router.get("/{template_id}", response_model=Dict[str, Any])
@handle_api_errors
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    Get template by ID
    
    Args:
        template_id: Template ID
        db: Database session
    
    Returns:
        Template information
    """
    try:
        template_service = DataTemplateService(db)
        template = template_service.get_template_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "success": True,
            "data": template
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.put("/{template_id}", response_model=Dict[str, Any])
@handle_api_errors
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update a template
    
    Args:
        template_id: Template ID to update
        request: Template update request
        db: Database session
    
    Returns:
        Updated template information
    """
    try:
        template_service = DataTemplateService(db)
        
        # Build update dict from request (only include non-None fields)
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.schema is not None:
            update_data["schema"] = request.schema
        if request.field_definitions is not None:
            update_data["field_definitions"] = request.field_definitions
        if request.example_data is not None:
            update_data["example_data"] = request.example_data
        
        template = template_service.update_template(template_id, **update_data)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "success": True,
            "data": template,
            "message": "Template updated successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/{template_id}", response_model=Dict[str, Any])
@handle_api_errors
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a template
    
    Args:
        template_id: Template ID to delete
        db: Database session
    
    Returns:
        Success status
    """
    try:
        template_service = DataTemplateService(db)
        success = template_service.delete_template(template_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "success": True,
            "message": "Template deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.post("/{template_id}/copy", response_model=Dict[str, Any])
@handle_api_errors
async def copy_template(
    template_id: int,
    request: Optional[TemplateCopyRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Copy a template
    
    Args:
        template_id: Template ID to copy
        request: Copy request with optional new name
        db: Database session
    
    Returns:
        New template information
    """
    try:
        template_service = DataTemplateService(db)
        new_name = request.name if request and request.name else None
        template = template_service.copy_template(template_id, new_name)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "success": True,
            "data": template,
            "message": "Template copied successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to copy template: {str(e)}")


@router.post("/parse-json", response_model=Dict[str, Any])
@handle_api_errors
async def parse_json(
    request: ParseJsonRequest,
    db: Session = Depends(get_db)
):
    """
    Parse JSON string to schema and field definitions
    
    Args:
        request: Parse JSON request
        db: Database session
    
    Returns:
        Parsed schema and field definitions
    """
    try:
        parser_service = JsonParserService()
        
        if request.use_agent:
            # Use AI agent for intelligent parsing
            try:
                field_parser_agent = FieldParserAgent(db=db)
                result = await parser_service.parse_json_with_agent(
                    request.json_string,
                    field_parser_agent
                )
            except Exception as agent_error:
                logger.warning(f"Agent parsing failed, falling back to basic parsing: {str(agent_error)}")
                # Fallback to basic parsing
                result = parser_service.parse_json(request.json_string)
        else:
            # Use basic parsing
            result = parser_service.parse_json(request.json_string)
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {str(e)}")
