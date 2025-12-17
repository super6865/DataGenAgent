"""
Schema merger service for merging template and document schemas
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SchemaMergerService:
    """Service for merging template and document schemas"""
    
    @staticmethod
    def merge_schemas(
        template_schema: Optional[Dict[str, Any]] = None,
        document_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge template and document schemas
        
        Priority: template > document > default
        
        Args:
            template_schema: Template JSON Schema (optional)
            document_schema: Document JSON Schema (optional)
        
        Returns:
            Merged JSON Schema
        """
        # If only one schema provided, return it
        if template_schema and not document_schema:
            return template_schema.copy()
        if document_schema and not template_schema:
            return document_schema.copy()
        if not template_schema and not document_schema:
            # Return default empty schema
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        # Merge both schemas
        merged_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Get properties from both schemas
        template_props = template_schema.get("properties", {})
        document_props = document_schema.get("properties", {})
        
        # Get all field names
        all_field_names = set(template_props.keys()) | set(document_props.keys())
        
        # Merge each field
        for field_name in all_field_names:
            template_field = template_props.get(field_name)
            document_field = document_props.get(field_name)
            
            if template_field and document_field:
                # Both exist: template takes priority, but merge constraints
                merged_field = SchemaMergerService._merge_field(
                    template_field, 
                    document_field, 
                    priority="template"
                )
            elif template_field:
                # Only in template
                merged_field = template_field.copy()
            else:
                # Only in document
                merged_field = document_field.copy()
            
            merged_schema["properties"][field_name] = merged_field
        
        # Merge required fields (union of both)
        template_required = set(template_schema.get("required", []))
        document_required = set(document_schema.get("required", []))
        # If field is required in template, it's required in merged schema
        merged_schema["required"] = list(template_required | document_required)
        
        return merged_schema
    
    @staticmethod
    def _merge_field(
        template_field: Dict[str, Any],
        document_field: Dict[str, Any],
        priority: str = "template"
    ) -> Dict[str, Any]:
        """
        Merge two field definitions
        
        Args:
            template_field: Template field definition
            document_field: Document field definition
            priority: "template" or "document" (which takes priority)
        
        Returns:
            Merged field definition
        """
        if priority == "template":
            merged = template_field.copy()
            # Merge constraints (take stricter ones)
            merged["constraints"] = SchemaMergerService._merge_constraints(
                template_field.get("constraints", {}),
                document_field.get("constraints", {})
            )
            # Merge description (prefer template, fallback to document)
            if not merged.get("description") and document_field.get("description"):
                merged["description"] = document_field["description"]
        else:
            merged = document_field.copy()
            # Merge constraints
            merged["constraints"] = SchemaMergerService._merge_constraints(
                document_field.get("constraints", {}),
                template_field.get("constraints", {})
            )
            # Merge description
            if not merged.get("description") and template_field.get("description"):
                merged["description"] = template_field["description"]
        
        # Handle nested objects
        if merged.get("type") == "object":
            template_props = template_field.get("properties", {})
            document_props = document_field.get("properties", {})
            if template_props or document_props:
                nested_schema = SchemaMergerService.merge_schemas(
                    {"properties": template_props, "required": template_field.get("required", [])},
                    {"properties": document_props, "required": document_field.get("required", [])}
                )
                merged["properties"] = nested_schema.get("properties", {})
                if nested_schema.get("required"):
                    merged["required"] = nested_schema["required"]
        
        # Handle arrays
        if merged.get("type") == "array":
            template_items = template_field.get("items", {})
            document_items = document_field.get("items", {})
            if template_items or document_items:
                # Merge array item schemas
                if template_items.get("type") == "object" and document_items.get("type") == "object":
                    nested_schema = SchemaMergerService.merge_schemas(
                        {"properties": template_items.get("properties", {}), "required": template_items.get("required", [])},
                        {"properties": document_items.get("properties", {}), "required": document_items.get("required", [])}
                    )
                    merged["items"] = {
                        "type": "object",
                        "properties": nested_schema.get("properties", {}),
                        "required": nested_schema.get("required", [])
                    }
                elif template_items:
                    merged["items"] = template_items.copy()
                else:
                    merged["items"] = document_items.copy()
        
        return merged
    
    @staticmethod
    def _merge_constraints(
        primary_constraints: Dict[str, Any],
        secondary_constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge constraints, taking stricter values
        
        Args:
            primary_constraints: Primary constraints (from priority source)
            secondary_constraints: Secondary constraints
        
        Returns:
            Merged constraints
        """
        merged = primary_constraints.copy()
        
        # String length constraints: take stricter range
        if "minLength" in primary_constraints and "minLength" in secondary_constraints:
            merged["minLength"] = max(primary_constraints["minLength"], secondary_constraints["minLength"])
        elif "minLength" in secondary_constraints:
            merged["minLength"] = secondary_constraints["minLength"]
        
        if "maxLength" in primary_constraints and "maxLength" in secondary_constraints:
            merged["maxLength"] = min(primary_constraints["maxLength"], secondary_constraints["maxLength"])
        elif "maxLength" in secondary_constraints:
            merged["maxLength"] = secondary_constraints["maxLength"]
        
        # Number constraints: take stricter range
        if "minimum" in primary_constraints and "minimum" in secondary_constraints:
            merged["minimum"] = max(primary_constraints["minimum"], secondary_constraints["minimum"])
        elif "minimum" in secondary_constraints:
            merged["minimum"] = secondary_constraints["minimum"]
        
        if "maximum" in primary_constraints and "maximum" in secondary_constraints:
            merged["maximum"] = min(primary_constraints["maximum"], secondary_constraints["maximum"])
        elif "maximum" in secondary_constraints:
            merged["maximum"] = secondary_constraints["maximum"]
        
        # Pattern: prefer primary, fallback to secondary
        if "pattern" not in merged and "pattern" in secondary_constraints:
            merged["pattern"] = secondary_constraints["pattern"]
        
        # Array constraints: take stricter range
        if "minItems" in primary_constraints and "minItems" in secondary_constraints:
            merged["minItems"] = max(primary_constraints["minItems"], secondary_constraints["minItems"])
        elif "minItems" in secondary_constraints:
            merged["minItems"] = secondary_constraints["minItems"]
        
        if "maxItems" in primary_constraints and "maxItems" in secondary_constraints:
            merged["maxItems"] = min(primary_constraints["maxItems"], secondary_constraints["maxItems"])
        elif "maxItems" in secondary_constraints:
            merged["maxItems"] = secondary_constraints["maxItems"]
        
        return merged
