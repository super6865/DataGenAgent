"""
Workflow router for routing data generation requests to appropriate workflow processors
"""
import re
import logging
from typing import Dict, Any, List, Optional
from app.api.v1.schemas import DocumentReference

logger = logging.getLogger(__name__)


class WorkflowRouter:
    """Router for directing data generation requests to appropriate workflow processors"""
    
    # Supported reference types
    REFERENCE_TYPE_DOCUMENT = "document"
    REFERENCE_TYPE_TEMPLATE = "template"
    REFERENCE_TYPE_DATASOURCE = "datasource"
    REFERENCE_TYPE_CUSTOM = "custom"
    
    # Supported workflow types
    WORKFLOW_TYPE_DOCUMENT = "document"
    WORKFLOW_TYPE_TEMPLATE = "template"
    WORKFLOW_TYPE_MIXED = "mixed"  # Template + Document
    WORKFLOW_TYPE_DATASOURCE = "datasource"
    WORKFLOW_TYPE_TEXT = "text"  # Default text-based generation
    
    def __init__(self):
        """Initialize workflow router"""
        pass
    
    def parse_references(
        self, 
        user_query: str, 
        references: Optional[List[DocumentReference]] = None
    ) -> Dict[str, Any]:
        """
        Parse references from user query and request
        
        Args:
            user_query: User's natural language query
            references: Optional list of document references from request
        
        Returns:
            Dict with parsed references and metadata:
            {
                "references": [...],
                "has_document_refs": bool,
                "has_template_refs": bool,
                "has_datasource_refs": bool,
                "has_custom_refs": bool,
                "reference_types": List[str]
            }
        """
        parsed_refs = []
        
        # Parse references from request if provided (these have valid IDs)
        if references:
            parsed_refs.extend(references)
        
        # Also parse @type:name format from user query
        # But only add references that don't already exist in parsed_refs
        # (to avoid duplicates and to prioritize references with valid IDs)
        query_refs = self._parse_query_references(user_query)
        if query_refs:
            # Create a set of existing reference names for quick lookup
            existing_refs = {(ref.type, ref.name.lower()) for ref in parsed_refs}
            
            # Only add query refs that don't already exist
            for query_ref in query_refs:
                ref_key = (query_ref.type, query_ref.name.lower())
                if ref_key not in existing_refs:
                    parsed_refs.append(query_ref)
        
        # Analyze reference types
        ref_types = [ref.type for ref in parsed_refs] if parsed_refs else []
        has_document = self.REFERENCE_TYPE_DOCUMENT in ref_types
        has_template = self.REFERENCE_TYPE_TEMPLATE in ref_types
        has_datasource = self.REFERENCE_TYPE_DATASOURCE in ref_types
        has_custom = self.REFERENCE_TYPE_CUSTOM in ref_types
        
        return {
            "references": parsed_refs,
            "has_document_refs": has_document,
            "has_template_refs": has_template,
            "has_datasource_refs": has_datasource,
            "has_custom_refs": has_custom,
            "reference_types": list(set(ref_types))
        }
    
    def _parse_query_references(self, user_query: str) -> List[DocumentReference]:
        """
        Parse @type:name format references from user query
        
        Args:
            user_query: User query string
        
        Returns:
            List of DocumentReference objects
        """
        references = []
        
        # Pattern: @type:name or @类型:名称
        pattern = r'@(\w+):([^\s@]+)'
        matches = re.findall(pattern, user_query)
        
        for ref_type, ref_name in matches:
            # Normalize reference type
            normalized_type = ref_type.lower()
            if normalized_type in ["文档", "document", "doc"]:
                normalized_type = self.REFERENCE_TYPE_DOCUMENT
            elif normalized_type in ["模板", "template", "tpl"]:
                normalized_type = self.REFERENCE_TYPE_TEMPLATE
            elif normalized_type in ["数据源", "datasource", "source"]:
                normalized_type = self.REFERENCE_TYPE_DATASOURCE
            elif normalized_type in ["自定义", "custom"]:
                normalized_type = self.REFERENCE_TYPE_CUSTOM
            else:
                # Default to document if type is unknown
                normalized_type = self.REFERENCE_TYPE_DOCUMENT
            
            # Create reference (without ID, will need to be resolved later)
            ref = DocumentReference(
                type=normalized_type,
                id=0,  # Will be resolved by workflow processor
                name=ref_name.strip()
            )
            references.append(ref)
        
        return references
    
    def route_to_workflow(
        self, 
        references: Optional[List[DocumentReference]] = None,
        parsed_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Determine which workflow processor to use based on references
        
        Args:
            references: List of document references
            parsed_info: Optional parsed reference info from parse_references()
        
        Returns:
            Workflow type string: "document", "template", "mixed", "datasource", or "text"
        """
        # Use parsed_info if provided, otherwise parse
        if parsed_info is None:
            parsed_info = self.parse_references("", references)
        
        # Check for mixed references (template + document)
        has_template = parsed_info.get("has_template_refs", False)
        has_document = parsed_info.get("has_document_refs", False)
        
        if has_template and has_document:
            # Mixed workflow: template + document
            return self.WORKFLOW_TYPE_MIXED
        elif has_template:
            # Template workflow
            return self.WORKFLOW_TYPE_TEMPLATE
        elif has_document:
            # Document workflow
            return self.WORKFLOW_TYPE_DOCUMENT
        elif parsed_info.get("has_datasource_refs", False):
            return self.WORKFLOW_TYPE_DATASOURCE
        elif parsed_info.get("has_custom_refs", False):
            # Custom references might need special handling
            # For now, route to text workflow
            return self.WORKFLOW_TYPE_TEXT
        else:
            # No references, use default text workflow
            return self.WORKFLOW_TYPE_TEXT
    
    def get_workflow_processor_class(self, workflow_type: str) -> Optional[str]:
        """
        Get the workflow processor class name for a given workflow type
        
        Args:
            workflow_type: Workflow type string
        
        Returns:
            Class name string or None
        """
        workflow_map = {
            self.WORKFLOW_TYPE_DOCUMENT: "DocumentWorkflowProcessor",
            self.WORKFLOW_TYPE_TEMPLATE: "TemplateWorkflowProcessor",
            self.WORKFLOW_TYPE_MIXED: "TemplateWorkflowProcessor",  # Use template processor for mixed
            self.WORKFLOW_TYPE_DATASOURCE: "DataSourceWorkflowProcessor",  # Reserved for future
            self.WORKFLOW_TYPE_TEXT: None  # Text workflow uses default DataGenerationAgent
        }
        
        return workflow_map.get(workflow_type)
    
    def should_use_workflow(self, references: Optional[List[DocumentReference]] = None) -> bool:
        """
        Check if workflow processing is needed
        
        Args:
            references: List of document references
        
        Returns:
            True if workflow processing is needed, False otherwise
        """
        if not references or len(references) == 0:
            return False
        
        # Check if any reference requires workflow processing
        parsed_info = self.parse_references("", references)
        return (
            parsed_info["has_document_refs"] or 
            parsed_info["has_template_refs"] or 
            parsed_info["has_datasource_refs"]
        )
    
    def get_document_references(
        self, 
        references: Optional[List[DocumentReference]] = None
    ) -> List[DocumentReference]:
        """
        Extract only document-type references
        
        Args:
            references: List of all references
        
        Returns:
            List of document references only (filtered to only include valid IDs)
        """
        if not references:
            return []
        
        # Filter document references and ensure they have valid IDs
        document_refs = [
            ref for ref in references 
            if ref.type == self.REFERENCE_TYPE_DOCUMENT and ref.id > 0
        ]
        
        return document_refs
    
    def get_datasource_references(
        self, 
        references: Optional[List[DocumentReference]] = None
    ) -> List[DocumentReference]:
        """
        Extract only datasource-type references (reserved for future)
        
        Args:
            references: List of all references
        
        Returns:
            List of datasource references only
        """
        if not references:
            return []
        
        return [
            ref for ref in references 
            if ref.type == self.REFERENCE_TYPE_DATASOURCE
        ]
    
    def get_template_references(
        self, 
        references: Optional[List[DocumentReference]] = None
    ) -> List[DocumentReference]:
        """
        Extract only template-type references
        
        Args:
            references: List of all references
        
        Returns:
            List of template references only (filtered to only include valid IDs)
        """
        if not references:
            return []
        
        # Filter template references and ensure they have valid IDs
        template_refs = [
            ref for ref in references 
            if ref.type == self.REFERENCE_TYPE_TEMPLATE and ref.id > 0
        ]
        
        return template_refs
