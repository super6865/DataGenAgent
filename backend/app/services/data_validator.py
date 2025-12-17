"""
Data validation service for validating generated data against JSON Schema
"""
import json
import logging
from typing import Dict, Any, List, Optional, Union
try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("jsonschema library not available. Schema validation will be limited.")

logger = logging.getLogger(__name__)


class DataValidator:
    """Service for validating data against JSON Schema"""
    
    def __init__(self):
        """Initialize data validator"""
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema library not installed. Install it with: pip install jsonschema")
    
    @staticmethod
    def _normalize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize JSON Schema to ensure it conforms to JSON Schema specification.
        
        This method recursively normalizes the schema:
        - Ensures all 'required' fields are arrays (not booleans)
        - Removes 'required' fields from property definitions (they shouldn't be there)
        - Handles nested objects and arrays
        
        Args:
            schema: JSON Schema dictionary to normalize
        
        Returns:
            Normalized JSON Schema dictionary
        """
        if not isinstance(schema, dict):
            return schema
        
        normalized = schema.copy()
        
        # Auto-unwrap common API response wrapper patterns (e.g., {response: {...}})
        # This handles cases where API docs define response wrapper, but generated data is direct items
        if "properties" in normalized and isinstance(normalized["properties"], dict):
            props = normalized["properties"]
            # Check if there's only one property that looks like a response wrapper
            if len(props) == 1:
                prop_name = list(props.keys())[0]
                prop_schema = props[prop_name]
                
                # Common wrapper names: response, data, result, body, content
                wrapper_names = ["response", "data", "result", "body", "content", "payload"]
                
                if prop_name.lower() in wrapper_names and isinstance(prop_schema, dict):
                    # Check if it's an object type with properties
                    if prop_schema.get("type") == "object" and "properties" in prop_schema:
                        # Unwrap: use the inner schema as the root schema
                        logger.debug(f"Auto-unwrapping '{prop_name}' wrapper in schema")
                        normalized = prop_schema.copy()
                        # Recursively normalize the unwrapped schema
                        normalized = DataValidator._normalize_schema(normalized)
                        return normalized
        
        # Normalize properties first to extract required fields from property definitions
        required_fields_from_props = []
        if "properties" in normalized and isinstance(normalized["properties"], dict):
            normalized_properties = {}
            
            for prop_name, prop_schema in normalized["properties"].items():
                if isinstance(prop_schema, dict):
                    # Recursively normalize nested schema
                    normalized_prop = DataValidator._normalize_schema(prop_schema)
                    
                    # Remove 'required' field from property definition (it shouldn't be there in JSON Schema)
                    # But if it exists and is True, add the field name to the required list
                    if "required" in normalized_prop:
                        prop_required = normalized_prop.pop("required")
                        # If it was a boolean True, add to required list
                        if prop_required is True:
                            required_fields_from_props.append(prop_name)
                        elif isinstance(prop_required, list) and prop_required:
                            # If it was a list, merge it (though this shouldn't happen in property definitions)
                            required_fields_from_props.extend([f"{prop_name}.{r}" for r in prop_required if isinstance(r, str)])
                    
                    normalized_properties[prop_name] = normalized_prop
                else:
                    normalized_properties[prop_name] = prop_schema
            
            normalized["properties"] = normalized_properties
        
        # Normalize 'required' field at schema/object level
        if "required" in normalized:
            required_value = normalized["required"]
            if isinstance(required_value, bool):
                if required_value is True:
                    # If required is True, use all property names as required fields
                    if normalized.get("properties") and isinstance(normalized["properties"], dict):
                        all_prop_names = list(normalized["properties"].keys())
                        normalized["required"] = list(set(all_prop_names + required_fields_from_props))
                    else:
                        # No properties, use fields extracted from property definitions
                        normalized["required"] = required_fields_from_props if required_fields_from_props else []
                else:
                    # If required is False, use only fields extracted from property definitions
                    normalized["required"] = required_fields_from_props if required_fields_from_props else []
            elif not isinstance(required_value, list):
                # If required is not a list, convert to array with fields from properties
                normalized["required"] = required_fields_from_props if required_fields_from_props else []
            else:
                # If it's already a list, merge with fields from property definitions
                if required_fields_from_props:
                    normalized["required"] = list(set(required_value + required_fields_from_props))
                # Otherwise keep the existing list
        else:
            # If no 'required' field exists, add one with fields extracted from property definitions
            if required_fields_from_props:
                normalized["required"] = required_fields_from_props
        
        # Normalize array items
        if "items" in normalized:
            items_schema = normalized["items"]
            if isinstance(items_schema, dict):
                normalized["items"] = DataValidator._normalize_schema(items_schema)
        
        # Normalize 'allOf', 'anyOf', 'oneOf' schemas
        for keyword in ["allOf", "anyOf", "oneOf"]:
            if keyword in normalized and isinstance(normalized[keyword], list):
                normalized[keyword] = [
                    DataValidator._normalize_schema(sub_schema) 
                    if isinstance(sub_schema, dict) 
                    else sub_schema
                    for sub_schema in normalized[keyword]
                ]
        
        return normalized
    
    def validate_against_schema(
        self,
        data: Any,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate data against JSON Schema
        
        Args:
            data: Data to validate (can be dict, list, or JSON string)
            schema: JSON Schema object
        
        Returns:
            Dict with validation result:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "details": List[Dict]
            }
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "details": []
        }
        
        try:
            # Normalize schema before validation to fix any format issues
            # Use deep copy to avoid modifying the original schema (which may be used for generation prompts)
            import copy
            normalized_schema = copy.deepcopy(schema)
            normalized_schema = self._normalize_schema(normalized_schema)
            
            # Parse data if it's a string
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    result["valid"] = False
                    result["errors"].append(f"Invalid JSON format: {str(e)}")
                    return result
            
            # If data is a list, validate each item
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    item_result = self._validate_item(item, normalized_schema, f"item[{idx}]")
                    if not item_result["valid"]:
                        result["valid"] = False
                        result["errors"].extend(item_result["errors"])
                        result["warnings"].extend(item_result["warnings"])
                        result["details"].extend(item_result["details"])
            else:
                # Validate single item
                item_result = self._validate_item(data, normalized_schema, "root")
                result["valid"] = item_result["valid"]
                result["errors"] = item_result["errors"]
                result["warnings"] = item_result["warnings"]
                result["details"] = item_result["details"]
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}", exc_info=True)
            result["valid"] = False
            result["errors"].append(f"Validation error: {str(e)}")
        
        return result
    
    def _validate_item(
        self,
        item: Any,
        schema: Dict[str, Any],
        path: str = "root"
    ) -> Dict[str, Any]:
        """
        Validate a single item against schema
        
        Args:
            item: Item to validate
            schema: JSON Schema
            path: Path prefix for error messages
        
        Returns:
            Validation result dict
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "details": []
        }
        
        if not JSONSCHEMA_AVAILABLE:
            # Fallback validation without jsonschema library
            return self._fallback_validation(item, schema, path)
        
        try:
            # Schema should already be normalized in validate_against_schema
            # But we normalize again here as a safety check (schema is already a copy)
            schema = self._normalize_schema(schema)
            
            # Use jsonschema library for validation
            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(item))
            
            if errors:
                result["valid"] = False
                for error in errors:
                    error_path = ".".join(str(p) for p in error.path) if error.path else path
                    error_msg = f"{error_path}: {error.message}"
                    result["errors"].append(error_msg)
                    result["details"].append({
                        "path": error_path,
                        "message": error.message,
                        "validator": error.validator,
                        "validator_value": error.validator_value
                    })
            
            # Additional custom validations
            custom_errors = self._check_custom_constraints(item, schema, path)
            result["errors"].extend(custom_errors)
            if custom_errors:
                result["valid"] = False
            
        except ValidationError as e:
            result["valid"] = False
            error_path = ".".join(str(p) for p in e.path) if e.path else path
            result["errors"].append(f"{error_path}: {e.message}")
            result["details"].append({
                "path": error_path,
                "message": e.message,
                "validator": e.validator,
                "validator_value": e.validator_value
            })
        except Exception as e:
            logger.error(f"Error in schema validation: {str(e)}", exc_info=True)
            result["valid"] = False
            result["errors"].append(f"Schema validation error: {str(e)}")
        
        return result
    
    def _fallback_validation(
        self,
        item: Any,
        schema: Dict[str, Any],
        path: str = "root"
    ) -> Dict[str, Any]:
        """
        Fallback validation without jsonschema library
        
        Args:
            item: Item to validate
            schema: JSON Schema
            path: Path prefix for error messages
        
        Returns:
            Validation result dict
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "details": []
        }
        
        if not isinstance(item, dict):
            result["valid"] = False
            result["errors"].append(f"{path}: Expected object, got {type(item).__name__}")
            return result
        
        schema_type = schema.get("type", "object")
        if schema_type != "object":
            # For non-object types, basic type check
            if schema_type == "array" and not isinstance(item, list):
                result["valid"] = False
                result["errors"].append(f"{path}: Expected array, got {type(item).__name__}")
            return result
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required fields
        for field in required:
            if field not in item:
                result["valid"] = False
                result["errors"].append(f"{path}.{field}: Required field is missing")
        
        # Check field types and constraints
        for field_name, field_value in item.items():
            field_path = f"{path}.{field_name}"
            field_schema = properties.get(field_name, {})
            
            if field_schema:
                # Check type
                expected_type = field_schema.get("type")
                if expected_type:
                    type_check = self._check_type(field_value, expected_type)
                    if not type_check["valid"]:
                        result["valid"] = False
                        result["errors"].append(f"{field_path}: {type_check['error']}")
                
                # Check constraints
                constraint_errors = self._check_field_constraints(field_value, field_schema, field_path)
                result["errors"].extend(constraint_errors)
                if constraint_errors:
                    result["valid"] = False
        
        return result
    
    def _check_type(self, value: Any, expected_type: str) -> Dict[str, Any]:
        """Check if value matches expected type"""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return {"valid": True, "error": None}
        
        if isinstance(expected_python_type, tuple):
            is_valid = isinstance(value, expected_python_type)
        else:
            is_valid = isinstance(value, expected_python_type)
        
        if not is_valid:
            return {
                "valid": False,
                "error": f"Expected {expected_type}, got {type(value).__name__}"
            }
        
        return {"valid": True, "error": None}
    
    def _check_field_constraints(
        self,
        field_value: Any,
        constraints: Dict[str, Any],
        field_path: str
    ) -> List[str]:
        """
        Check field value against constraints
        
        Args:
            field_value: Field value to check
            constraints: Constraint dictionary from schema
            field_path: Field path for error messages
        
        Returns:
            List of error messages
        """
        errors = []
        constraint_def = constraints.get("constraints", {})
        
        # If constraints are at the top level, use them directly
        if not constraint_def and isinstance(constraints, dict):
            constraint_def = constraints
        
        field_type = constraints.get("type", type(field_value).__name__)
        
        # String constraints
        if field_type == "string" and isinstance(field_value, str):
            min_length = constraint_def.get("minLength")
            max_length = constraint_def.get("maxLength")
            pattern = constraint_def.get("pattern")
            enum = constraint_def.get("enum")
            
            if min_length is not None and len(field_value) < min_length:
                errors.append(f"{field_path}: String length {len(field_value)} is less than minimum {min_length}")
            
            if max_length is not None and len(field_value) > max_length:
                errors.append(f"{field_path}: String length {len(field_value)} exceeds maximum {max_length}")
            
            if pattern:
                import re
                if not re.match(pattern, field_value):
                    errors.append(f"{field_path}: String does not match pattern {pattern}")
            
            if enum and field_value not in enum:
                errors.append(f"{field_path}: Value '{field_value}' is not in enum {enum}")
        
        # Number constraints
        elif field_type in ["number", "integer"] and isinstance(field_value, (int, float)):
            minimum = constraint_def.get("minimum")
            maximum = constraint_def.get("maximum")
            enum = constraint_def.get("enum")
            
            if minimum is not None and field_value < minimum:
                errors.append(f"{field_path}: Value {field_value} is less than minimum {minimum}")
            
            if maximum is not None and field_value > maximum:
                errors.append(f"{field_path}: Value {field_value} exceeds maximum {maximum}")
            
            if enum and field_value not in enum:
                errors.append(f"{field_path}: Value {field_value} is not in enum {enum}")
        
        # Array constraints
        elif field_type == "array" and isinstance(field_value, list):
            min_items = constraint_def.get("minItems")
            max_items = constraint_def.get("maxItems")
            
            if min_items is not None and len(field_value) < min_items:
                errors.append(f"{field_path}: Array length {len(field_value)} is less than minimum {min_items}")
            
            if max_items is not None and len(field_value) > max_items:
                errors.append(f"{field_path}: Array length {len(field_value)} exceeds maximum {max_items}")
        
        return errors
    
    def _check_custom_constraints(
        self,
        item: Any,
        schema: Dict[str, Any],
        path: str
    ) -> List[str]:
        """
        Check custom constraints beyond standard JSON Schema
        
        Args:
            item: Item to validate
            schema: JSON Schema
            path: Path prefix for error messages
        
        Returns:
            List of error messages
        """
        errors = []
        
        # Add custom validation logic here if needed
        # For example: cross-field validation, business rule validation, etc.
        
        return errors
