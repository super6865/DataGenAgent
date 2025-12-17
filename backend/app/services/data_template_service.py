"""
Data template service for managing data templates
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.data_template import DataTemplate
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class DataTemplateService:
    """Service for managing data templates"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_template(
        self,
        name: str,
        schema: Dict[str, Any],
        field_definitions: List[Dict[str, Any]],
        description: Optional[str] = None,
        example_data: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new data template
        
        Args:
            name: Template name (1-50 characters)
            schema: JSON Schema structure
            field_definitions: Field definitions list
            description: Template description (optional)
            example_data: Example data (optional)
            created_by: User ID who created the template
        
        Returns:
            Template information dict
        """
        try:
            # Validate name length
            if not name or len(name.strip()) == 0:
                raise ValueError("Template name cannot be empty")
            if len(name) > 50:
                raise ValueError("Template name cannot exceed 50 characters")
            
            # Check for duplicate template name
            existing_template = self.db.query(DataTemplate).filter(DataTemplate.name == name).first()
            if existing_template:
                raise ValueError(f"Template name '{name}' already exists")
            
            # Validate schema and field_definitions with detailed error messages
            logger.debug(f"Received schema type: {type(schema)}, field_definitions type: {type(field_definitions)}")
            
            if not schema:
                raise ValueError("Schema cannot be empty")
            if not isinstance(schema, dict):
                raise ValueError(f"Schema must be a valid JSON object, got {type(schema).__name__}")
            
            # Handle field_definitions validation with type conversion
            if field_definitions is None:
                raise ValueError("Field definitions cannot be None")
            
            # Try to convert to list if it's not already
            if not isinstance(field_definitions, list):
                logger.warning(f"field_definitions is not a list, got {type(field_definitions).__name__}, attempting conversion")
                # If it's a string, try to parse it as JSON
                if isinstance(field_definitions, str):
                    try:
                        field_definitions = json.loads(field_definitions)
                    except json.JSONDecodeError:
                        raise ValueError(f"Field definitions must be a valid JSON array, got string that cannot be parsed")
                
                # Check again after potential conversion
                if not isinstance(field_definitions, list):
                    raise ValueError(f"Field definitions must be a valid JSON array, got {type(field_definitions).__name__}")
            
            # Validate that it's not an empty list - require at least one field
            if len(field_definitions) == 0:
                raise ValueError("At least one field definition is required to create a template")
            
            # Validate each field definition has required fields
            valid_field_count = 0
            for idx, field in enumerate(field_definitions):
                if not isinstance(field, dict):
                    raise ValueError(f"Field definition at index {idx} must be an object, got {type(field).__name__}")
                if "name" not in field or not field["name"]:
                    raise ValueError(f"Field definition at index {idx} must have a 'name' field")
                if "type" not in field:
                    raise ValueError(f"Field definition at index {idx} must have a 'type' field")
                valid_field_count += 1
            
            # Ensure at least one valid field
            if valid_field_count == 0:
                raise ValueError("At least one valid field definition is required to create a template")
            
            # Create template
            template = DataTemplate(
                name=name.strip(),
                description=description,
                schema=schema,
                field_definitions=field_definitions,
                example_data=example_data,
                created_by=created_by
            )
            
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"Template created successfully: {template.id} - {name}")
            
            return self._template_to_dict(template)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating template: {str(e)}", exc_info=True)
            raise
    
    def get_template_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get template by ID"""
        template = self.db.query(DataTemplate).filter(DataTemplate.id == template_id).first()
        if not template:
            return None
        return self._template_to_dict(template)
    
    def get_templates(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get templates list with pagination and search
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search keyword for template name or description
        
        Returns:
            Tuple of (templates list, total count)
        """
        try:
            query = self.db.query(DataTemplate)
            
            # Apply search filter
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    or_(
                        DataTemplate.name.like(search_pattern),
                        DataTemplate.description.like(search_pattern)
                    )
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            templates = query.order_by(DataTemplate.created_at.desc()).offset(skip).limit(limit).all()
            
            result = [self._template_to_dict(template) for template in templates]
            
            return result, total
            
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}", exc_info=True)
            return [], 0
    
    def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        field_definitions: Optional[List[Dict[str, Any]]] = None,
        example_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a template
        
        Args:
            template_id: Template ID to update
            name: New template name (optional)
            description: New template description (optional)
            schema: New JSON Schema structure (optional)
            field_definitions: New field definitions list (optional)
            example_data: New example data (optional)
        
        Returns:
            Updated template information dict, or None if not found
        """
        try:
            template = self.db.query(DataTemplate).filter(DataTemplate.id == template_id).first()
            if not template:
                return None
            
            # Update fields if provided
            if name is not None:
                if len(name.strip()) == 0:
                    raise ValueError("Template name cannot be empty")
                if len(name) > 50:
                    raise ValueError("Template name cannot exceed 50 characters")
                # Check for duplicate name (excluding current template)
                existing_template = self.db.query(DataTemplate).filter(
                    DataTemplate.name == name,
                    DataTemplate.id != template_id
                ).first()
                if existing_template:
                    raise ValueError(f"Template name '{name}' already exists")
                template.name = name.strip()
            
            if description is not None:
                template.description = description
            
            if schema is not None:
                if not isinstance(schema, dict):
                    raise ValueError("Schema must be a valid JSON object")
                template.schema = schema
            
            if field_definitions is not None:
                if not isinstance(field_definitions, list):
                    raise ValueError("Field definitions must be a valid JSON array")
                template.field_definitions = field_definitions
            
            if example_data is not None:
                template.example_data = example_data
            
            template.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"Template updated successfully: {template_id}")
            
            return self._template_to_dict(template)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating template: {str(e)}", exc_info=True)
            raise
    
    def delete_template(self, template_id: int) -> bool:
        """
        Delete a template
        
        Args:
            template_id: Template ID to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            template = self.db.query(DataTemplate).filter(DataTemplate.id == template_id).first()
            if not template:
                return False
            
            self.db.delete(template)
            self.db.commit()
            
            logger.info(f"Template deleted successfully: {template_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting template: {str(e)}", exc_info=True)
            return False
    
    def copy_template(self, template_id: int, new_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Copy a template
        
        Args:
            template_id: Template ID to copy
            new_name: New template name (optional, defaults to "Copy of {original_name}")
        
        Returns:
            New template information dict, or None if source template not found
        """
        try:
            source_template = self.db.query(DataTemplate).filter(DataTemplate.id == template_id).first()
            if not source_template:
                return None
            
            # Generate new name if not provided
            if not new_name:
                new_name = f"Copy of {source_template.name}"
            
            # Check if new name already exists
            existing_template = self.db.query(DataTemplate).filter(DataTemplate.name == new_name).first()
            if existing_template:
                # Append number to make it unique
                counter = 1
                while True:
                    candidate_name = f"{new_name} ({counter})"
                    existing = self.db.query(DataTemplate).filter(DataTemplate.name == candidate_name).first()
                    if not existing:
                        new_name = candidate_name
                        break
                    counter += 1
            
            # Create new template
            new_template = DataTemplate(
                name=new_name,
                description=source_template.description,
                schema=source_template.schema.copy() if source_template.schema else {},
                field_definitions=source_template.field_definitions.copy() if source_template.field_definitions else [],
                example_data=source_template.example_data.copy() if source_template.example_data else None,
                created_by=source_template.created_by
            )
            
            self.db.add(new_template)
            self.db.commit()
            self.db.refresh(new_template)
            
            logger.info(f"Template copied successfully: {template_id} -> {new_template.id}")
            
            return self._template_to_dict(new_template)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error copying template: {str(e)}", exc_info=True)
            raise
    
    def _template_to_dict(self, template: DataTemplate) -> Dict[str, Any]:
        """Convert template model to dict"""
        # Calculate field count from field_definitions
        field_count = len(template.field_definitions) if template.field_definitions else 0
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "schema": template.schema,
            "field_definitions": template.field_definitions,
            "example_data": template.example_data,
            "field_count": field_count,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
