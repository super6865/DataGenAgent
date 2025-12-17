"""
JSON parser service for parsing JSON strings to schema and field definitions
"""
import json
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Maximum nesting depth to prevent infinite recursion
MAX_DEPTH = 10

# Date and datetime patterns
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}')


class JsonParserService:
    """Service for parsing JSON strings to schema and field definitions"""
    
    @staticmethod
    def infer_field_type(value: Any) -> str:
        """
        Infer field type from value
        
        Args:
            value: Field value
            
        Returns:
            Field type string
        """
        if value is None:
            return "string"  # Default to string for null values
        
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            # Check if it's a date or datetime
            if DATE_PATTERN.match(value):
                return "date"
            elif DATETIME_PATTERN.match(value):
                return "datetime"
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"  # Default fallback
    
    @staticmethod
    def generate_field_description(field_name: str) -> str:
        """
        Generate default field description based on field name
        
        Args:
            field_name: Field name
            
        Returns:
            Default description
        """
        # Convert camelCase or snake_case to readable text
        # e.g., "userName" -> "用户名称", "user_name" -> "用户名称"
        name = field_name.replace('_', ' ').replace('-', ' ')
        # Simple mapping for common field names
        mappings = {
            'name': '名称',
            'id': 'ID',
            'age': '年龄',
            'email': '邮箱',
            'phone': '电话',
            'address': '地址',
            'city': '城市',
            'country': '国家',
            'date': '日期',
            'time': '时间',
            'created': '创建时间',
            'updated': '更新时间',
        }
        
        for key, value in mappings.items():
            if key in name.lower():
                return value
        
        # Default: use field name as description
        return name
    
    @staticmethod
    def infer_constraints(field_name: str, value: Any, field_type: str) -> Dict[str, Any]:
        """
        Infer constraints from example value
        
        Args:
            field_name: Field name
            value: Example value
            field_type: Field type
            
        Returns:
            Constraints dictionary
        """
        constraints = {}
        
        if field_type == "string" and isinstance(value, str):
            length = len(value)
            if length > 0:
                constraints["minLength"] = 1
                constraints["maxLength"] = length * 2  # Allow some flexibility
                
            # Check for email pattern
            if "@" in value and "." in value:
                constraints["pattern"] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        
        elif field_type in ["integer", "number"]:
            if isinstance(value, (int, float)):
                constraints["minimum"] = value * 0.5 if value > 0 else value - 10
                constraints["maximum"] = value * 2 if value > 0 else value + 10
        
        elif field_type == "array" and isinstance(value, list):
            constraints["minItems"] = 0
            constraints["maxItems"] = len(value) * 2 if len(value) > 0 else 10
        
        return constraints
    
    def _extract_fields(
        self,
        obj: Union[Dict, List],
        prefix: str = "",
        depth: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Recursively extract fields from JSON object
        
        Args:
            obj: JSON object or array
            prefix: Field path prefix
            depth: Current nesting depth
            
        Returns:
            List of field definitions
        """
        if depth > MAX_DEPTH:
            logger.warning(f"Maximum nesting depth {MAX_DEPTH} reached")
            return []
        
        fields = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_path = f"{prefix}.{key}" if prefix else key
                field_type = self.infer_field_type(value)
                
                field_def = {
                    "name": key,
                    "path": field_path,
                    "type": field_type,
                    "description": self.generate_field_description(key),
                    "required": False,  # Default to not required
                    "constraints": {}
                }
                
                # Add constraints
                constraints = self.infer_constraints(key, value, field_type)
                if constraints:
                    field_def["constraints"] = constraints
                
                # Handle nested structures
                if field_type == "object" and isinstance(value, dict):
                    # Add nested fields - recursively extract all nested properties
                    nested_fields = self._extract_fields(value, field_path, depth + 1)
                    if nested_fields:
                        field_def["properties"] = nested_fields
                        logger.debug(f"Extracted {len(nested_fields)} nested properties for object field '{key}'")
                elif field_type == "array" and isinstance(value, list) and len(value) > 0:
                    # Infer array item type
                    item_type = self.infer_field_type(value[0])
                    field_def["items"] = {
                        "type": item_type
                    }
                    # If array contains objects, extract their structure recursively
                    if item_type == "object" and isinstance(value[0], dict):
                        nested_fields = self._extract_fields(value[0], f"{field_path}[]", depth + 1)
                        if nested_fields:
                            field_def["items"]["properties"] = nested_fields
                            logger.debug(f"Extracted {len(nested_fields)} nested properties for array items in field '{key}'")
                
                fields.append(field_def)
        
        elif isinstance(obj, list) and len(obj) > 0:
            # Handle array at root level
            item_type = self.infer_field_type(obj[0])
            if item_type == "object" and isinstance(obj[0], dict):
                fields = self._extract_fields(obj[0], prefix, depth + 1)
        
        return fields
    
    def _build_schema(
        self,
        field_definitions: List[Dict[str, Any]],
        root_path: str = ""
    ) -> Dict[str, Any]:
        """
        Build JSON Schema from field definitions
        
        Args:
            field_definitions: List of field definitions
            root_path: Root path for filtering fields
            
        Returns:
            JSON Schema dictionary
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for field in field_definitions:
            # Only include top-level fields in root schema
            if "." not in field.get("path", field["name"]):
                field_name = field["name"]
                field_schema = {
                    "type": field["type"],
                    "description": field.get("description", "")
                }
                
                # Add constraints
                if field.get("constraints"):
                    field_schema.update(field["constraints"])
                
                # Handle nested objects
                if field["type"] == "object" and field.get("properties"):
                    nested_schema = self._build_schema(field["properties"], field["path"])
                    field_schema["properties"] = nested_schema.get("properties", {})
                    nested_required = nested_schema.get("required")
                    if nested_required:
                        # Ensure required is a list, not a boolean
                        if isinstance(nested_required, list):
                            field_schema["required"] = nested_required
                        else:
                            # If it's not a list, convert to empty list (safety check)
                            logger.warning(f"Nested schema 'required' field is not a list for field '{field_name}', ignoring")
                            field_schema["required"] = []
                
                # Handle arrays
                elif field["type"] == "array" and field.get("items"):
                    field_schema["items"] = field["items"]
                    if field["items"].get("type") == "object" and field["items"].get("properties"):
                        nested_schema = self._build_schema(field["items"]["properties"], field["path"])
                        field_schema["items"]["properties"] = nested_schema.get("properties", {})
                        nested_required = nested_schema.get("required")
                        if nested_required:
                            # Ensure required is a list, not a boolean
                            if isinstance(nested_required, list):
                                field_schema["items"]["required"] = nested_required
                            else:
                                # If it's not a list, convert to empty list (safety check)
                                logger.warning(f"Array items schema 'required' field is not a list for field '{field_name}', ignoring")
                                field_schema["items"]["required"] = []
                
                schema["properties"][field_name] = field_schema
                
                # Add to required if marked as required
                if field.get("required", False):
                    schema["required"].append(field_name)
        
        return schema
    
    def parse_json_to_schema(self, json_string: str) -> Dict[str, Any]:
        """
        Parse JSON string to JSON Schema
        
        Args:
            json_string: JSON string to parse
            
        Returns:
            JSON Schema dictionary
        """
        try:
            # Parse JSON string
            data = json.loads(json_string)
            
            # Extract field definitions
            field_definitions = self._extract_fields(data)
            
            # Build schema
            schema = self._build_schema(field_definitions)
            
            return schema
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing JSON to schema: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse JSON: {str(e)}")
    
    def parse_json_to_field_definitions(self, json_string: str) -> List[Dict[str, Any]]:
        """
        Parse JSON string to field definitions list
        
        Args:
            json_string: JSON string to parse
            
        Returns:
            List of field definitions
        """
        try:
            # Parse JSON string
            data = json.loads(json_string)
            
            # Extract field definitions
            field_definitions = self._extract_fields(data)
            
            # Clean up field definitions (remove path, keep only necessary fields)
            def clean_field(field: Dict[str, Any]) -> Dict[str, Any]:
                cleaned_field = {
                    "name": field["name"],
                    "type": field["type"],
                    "description": field.get("description", ""),
                    "required": field.get("required", False),
                    "constraints": field.get("constraints", {})
                }
                
                # Handle nested structures - recursively clean nested fields
                if field["type"] == "object" and field.get("properties"):
                    # Recursively clean all nested properties
                    nested_properties = []
                    for nested_field in field["properties"]:
                        nested_properties.append(clean_field(nested_field))
                    cleaned_field["properties"] = nested_properties
                    logger.debug(f"Cleaned object field '{field['name']}' with {len(nested_properties)} nested properties")
                    
                elif field["type"] == "array" and field.get("items"):
                    items = field["items"].copy()
                    # Handle array items that are objects with nested properties
                    if items.get("type") == "object" and items.get("properties"):
                        # Recursively clean nested properties in array items
                        nested_properties = []
                        for nested_field in items["properties"]:
                            nested_properties.append(clean_field(nested_field))
                        items["properties"] = nested_properties
                        logger.debug(f"Cleaned array field '{field['name']}' with object items containing {len(nested_properties)} properties")
                    cleaned_field["items"] = items
                
                return cleaned_field
            
            cleaned_definitions = [clean_field(field) for field in field_definitions]
            
            return cleaned_definitions
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing JSON to field definitions: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse JSON: {str(e)}")
    
    def parse_json(
        self,
        json_string: str
    ) -> Dict[str, Any]:
        """
        Parse JSON string to both schema and field definitions
        
        Args:
            json_string: JSON string to parse
            
        Returns:
            Dictionary with schema and field_definitions
        """
        # Validate JSON size (prevent DoS)
        if len(json_string) > 1024 * 1024:  # 1MB limit
            raise ValueError("JSON string too large (maximum 1MB)")
        
        schema = self.parse_json_to_schema(json_string)
        field_definitions = self.parse_json_to_field_definitions(json_string)
        
        return {
            "schema": schema,
            "field_definitions": field_definitions
        }
    
    async def parse_json_with_agent(
        self,
        json_string: str,
        field_parser_agent: Any
    ) -> Dict[str, Any]:
        """
        Parse JSON string using AI agent for intelligent field extraction
        
        Args:
            json_string: JSON string to parse
            field_parser_agent: FieldParserAgent instance
            
        Returns:
            Dictionary with schema and field_definitions
        """
        # Validate JSON size (prevent DoS)
        if len(json_string) > 1024 * 1024:  # 1MB limit
            raise ValueError("JSON string too large (maximum 1MB)")
        
        try:
            # Use agent to parse
            result = await field_parser_agent.parse_json(json_string)
            return result
        except Exception as e:
            logger.error(f"Agent parsing failed, falling back to basic parsing: {str(e)}")
            # Fallback to basic parsing
            return self.parse_json(json_string)
