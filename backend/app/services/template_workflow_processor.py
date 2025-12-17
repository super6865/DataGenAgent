"""
Template workflow processor for handling template-based data generation
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.services.data_template_service import DataTemplateService
from app.services.schema_merger_service import SchemaMergerService
from app.services.document_workflow_processor import DocumentWorkflowProcessor
from app.services.llm_service import DataGenerationAgent
from app.services.observability_service import ObservabilityService
from app.api.v1.schemas import DocumentReference
import time

logger = logging.getLogger(__name__)


class TemplateWorkflowProcessor:
    """Processor for template-based data generation workflow"""
    
    def __init__(self, db: Session, model_config_dict: Dict[str, Any]):
        """
        Initialize template workflow processor
        
        Args:
            db: Database session
            model_config_dict: Model configuration dictionary
        """
        self.db = db
        self.model_config_dict = model_config_dict
        self.template_service = DataTemplateService(db)
        self.schema_merger = SchemaMergerService()
    
    async def process_template_workflow(
        self,
        template_refs: List[DocumentReference],
        user_query: str,
        format_hint: Optional[str] = None,
        document_refs: Optional[List[DocumentReference]] = None,
        document_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        observability_service: Optional[ObservabilityService] = None
    ) -> Dict[str, Any]:
        """
        Process template workflow for data generation
        
        Workflow steps:
        1. Load template(s) and extract schema(s)
        2. Merge multiple templates if needed
        3. Merge with document schema if provided
        4. Enhance user query with template schema
        5. Generate data using enhanced query
        6. Return generated data with context information
        
        Args:
            template_refs: List of template references
            user_query: User's natural language query
            format_hint: Optional format hint (json, csv, excel, text)
            document_refs: Optional document references (for mixed workflow)
            document_context: Optional document context (for mixed workflow)
            trace_id: Optional trace ID for observability
            observability_service: Optional observability service instance
        
        Returns:
            Dict with generated data and workflow metadata
        """
        workflow_start_time = time.time()
        workflow_span_id = None
        
        try:
            # Span: Template workflow
            if trace_id and observability_service:
                workflow_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="template_workflow",
                    kind="internal",
                    attributes={
                        "template_count": len(template_refs),
                        "user_query": user_query,
                        "format_hint": format_hint,
                        "has_document_refs": document_refs is not None and len(document_refs) > 0
                    }
                )
                workflow_span_id = workflow_span.get('data', {}).get('span_id') if workflow_span.get('success') else None
            
            # Step 1: Load templates and extract schemas
            template_schemas = []
            template_metadata = []
            
            for template_ref in template_refs:
                # Resolve template by name
                templates, _ = self.template_service.get_templates(
                    skip=0,
                    limit=1,
                    search=template_ref.name
                )
                
                if not templates:
                    raise ValueError(f"Template not found: {template_ref.name}")
                
                template = templates[0]
                if template["id"] != template_ref.id and template_ref.id != 0:
                    # If ID was provided, verify it matches
                    template_by_id = self.template_service.get_template_by_id(template_ref.id)
                    if template_by_id:
                        template = template_by_id
                
                template_schemas.append(template["schema"])
                template_metadata.append({
                    "id": template["id"],
                    "name": template["name"],
                    "description": template.get("description")
                })
            
            # Step 2: Merge multiple templates if needed
            merged_template_schema = template_schemas[0] if len(template_schemas) == 1 else None
            if len(template_schemas) > 1:
                # Merge multiple templates (first template as base, others merged in)
                merged_template_schema = template_schemas[0]
                for schema in template_schemas[1:]:
                    merged_template_schema = self.schema_merger.merge_schemas(
                        template_schema=merged_template_schema,
                        document_schema=schema
                    )
            
            # Step 3: Merge with document schema if provided
            final_schema = merged_template_schema
            if document_context and document_context.get("context_type") == "schema":
                document_schema = document_context.get("schema")
                if document_schema:
                    final_schema = self.schema_merger.merge_schemas(
                        template_schema=merged_template_schema,
                        document_schema=document_schema
                    )
            
            # Step 4: Enhance user query with template schema
            enhanced_query = self._enhance_query_with_schema(user_query, final_schema)
            
            # Step 5: Generate data using enhanced query
            agent = DataGenerationAgent(self.model_config_dict)
            
            # generate_data returns (generated_data: str, usage: Dict[str, int])
            generated_data, usage = await agent.generate_data(
                user_query=enhanced_query,
                format_hint=format_hint,
                trace_id=trace_id,
                observability_service=observability_service
            )
            
            # Step 6: Return result
            workflow_metadata = {
                "workflow_type": "template",
                "template_count": len(template_refs),
                "templates": template_metadata,
                "has_document_refs": document_refs is not None and len(document_refs) > 0,
                "schema_source": "template" if not document_context else "merged"
            }
            
            return {
                "success": True,
                "generated_data": generated_data,
                "usage": usage,
                "workflow_metadata": workflow_metadata,
                "template_context": {
                    "context_type": "schema",
                    "schema": final_schema,
                    "templates": template_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"Template workflow failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "generated_data": "",
                "usage": {},
                "workflow_metadata": {}
            }
    
    def _enhance_query_with_schema(
        self,
        user_query: str,
        schema: Dict[str, Any]
    ) -> str:
        """
        Enhance user query with template schema information
        
        Args:
            user_query: Original user query
            schema: JSON Schema to include
        
        Returns:
            Enhanced query string
        """
        import json
        
        schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
        
        enhanced_query = f"""请根据以下JSON Schema结构生成数据：

{schema_str}

用户需求：{user_query}

请严格按照Schema中定义的字段、类型和约束条件生成数据。"""
        
        return enhanced_query
