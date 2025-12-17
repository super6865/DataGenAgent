"""
Document workflow processor for handling document-based data generation
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.document import Document
from app.services.document_service import DocumentService
from app.services.document_parsing_task import DocumentParsingTask
from app.agents.intent_recognition_agent import IntentRecognitionAgent
from app.agents.data_structure_agent import DataStructureAgent
from app.agents.test_point_agent import TestPointAgent
from app.services.llm_service import DataGenerationAgent
from app.services.observability_service import ObservabilityService
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class DocumentWorkflowProcessor:
    """Processor for document-based data generation workflow"""
    
    def __init__(self, db: Session, model_config_dict: Dict[str, Any]):
        """
        Initialize document workflow processor
        
        Args:
            db: Database session
            model_config_dict: Model configuration dictionary
        """
        self.db = db
        self.model_config_dict = model_config_dict
        self.document_service = DocumentService(db)
        self.parsing_task = DocumentParsingTask(db)
    
    async def process_document_workflow(
        self,
        document_id: int,
        user_query: str,
        format_hint: Optional[str] = None,
        trace_id: Optional[str] = None,
        observability_service: Optional[ObservabilityService] = None
    ) -> Dict[str, Any]:
        """
        Process document workflow for data generation
        
        Workflow steps:
        1. Ensure document is parsed and document type is recognized
        2. Extract document context (schema or test points) based on document type
        3. Enhance user query with document context
        4. Generate data using enhanced query
        5. Return generated data with context information
        
        Args:
            document_id: Document ID
            user_query: User's natural language query
            format_hint: Optional format hint (json, csv, excel, text)
            trace_id: Optional trace ID for observability
            observability_service: Optional observability service instance
        
        Returns:
            Dict with generated data and workflow metadata
        """
        workflow_start_time = time.time()
        workflow_span_id = None
        
        try:
            # Span: Document workflow
            if trace_id and observability_service:
                workflow_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="document_workflow",
                    kind="internal",
                    attributes={
                        "document_id": document_id,
                        "user_query": user_query,
                        "format_hint": format_hint
                    }
                )
                workflow_span_id = workflow_span.get('data', {}).get('span_id') if workflow_span.get('success') else None
            
            # Step 1: Ensure document is parsed and type is recognized
            document_info = await self._ensure_document_parsed(document_id, trace_id, observability_service, workflow_span_id)
            document_type = document_info.get("document_type", "unknown")
            
            # Step 2: Extract document context based on document type
            document_context = await self._extract_document_context(
                document_id, 
                document_type, 
                document_info,
                trace_id, 
                observability_service, 
                workflow_span_id
            )
            
            # Step 3: Enhance user query with document context
            enhanced_query = self._enhance_query_with_context(user_query, document_context, document_type)
            
            # Step 4: Generate data using enhanced query
            data_generation_agent = DataGenerationAgent(self.model_config_dict)
            generated_content, usage = await data_generation_agent.generate_data(
                user_query=enhanced_query,
                format_hint=format_hint,
                trace_id=trace_id,
                observability_service=observability_service
            )
            
            # Step 5: Update workflow span
            if trace_id and observability_service and workflow_span_id:
                workflow_duration = (time.time() - workflow_start_time) * 1000
                observability_service.update_span(
                    span_id=workflow_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=workflow_duration,
                    status_code="OK",
                    attributes={
                        "document_type": document_type,
                        "context_extracted": bool(document_context),
                        "usage": usage
                    }
                )
            
            return {
                "success": True,
                "generated_data": generated_content,
                "format": format_hint or "json",
                "usage": usage,
                "workflow_metadata": {
                    "document_id": document_id,
                    "document_type": document_type,
                    "context_extracted": bool(document_context),
                    "context_type": document_context.get("context_type") if document_context else None
                },
                "document_context": document_context  # Include context for validation
            }
            
        except Exception as e:
            logger.error(f"Error in document workflow: {str(e)}", exc_info=True)
            
            # Update workflow span with error
            if trace_id and observability_service and workflow_span_id:
                workflow_duration = (time.time() - workflow_start_time) * 1000
                observability_service.update_span(
                    span_id=workflow_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=workflow_duration,
                    status_code="ERROR",
                    status_message=str(e)
                )
            
            raise
    
    async def _ensure_document_parsed(
        self,
        document_id: int,
        trace_id: Optional[str] = None,
        observability_service: Optional[ObservabilityService] = None,
        parent_span_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ensure document is parsed and document type is recognized
        
        Args:
            document_id: Document ID
            trace_id: Optional trace ID
            observability_service: Optional observability service
            parent_span_id: Optional parent span ID
        
        Returns:
            Document information dict
        """
        ensure_span_id = None
        ensure_start = time.time()
        
        try:
            # Span: Ensure document parsed
            if trace_id and observability_service:
                ensure_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="ensure_document_parsed",
                    kind="internal",
                    parent_span_id=parent_span_id,
                    attributes={"document_id": document_id}
                )
                ensure_span_id = ensure_span.get('data', {}).get('span_id') if ensure_span.get('success') else None
            
            # Get document
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Check if document needs parsing
            needs_parsing = (
                document.parse_status != "success" or 
                not document.parse_result or
                document.document_type in [None, "unknown"]
            )
            
            if needs_parsing:
                logger.info(f"Document {document_id} needs parsing, starting parse with intent...")
                # Parse document with intent recognition
                parse_result = await self.parsing_task.parse_document_with_intent(
                    document_id,
                    trace_id=trace_id,
                    observability_service=observability_service,
                    parent_span_id=ensure_span_id
                )
                if not parse_result.get("success"):
                    raise ValueError(f"Failed to parse document: {parse_result.get('error', 'Unknown error')}")
                
                # Refresh document to get updated info
                self.db.refresh(document)
            
            # Extract document info
            parse_result = document.parse_result or {}
            document_type = document.document_type or "unknown"
            
            # Update span
            if trace_id and observability_service and ensure_span_id:
                ensure_duration = (time.time() - ensure_start) * 1000
                observability_service.update_span(
                    span_id=ensure_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=ensure_duration,
                    status_code="OK",
                    attributes={
                        "parse_status": document.parse_status,
                        "document_type": document_type,
                        "needed_parsing": needs_parsing
                    }
                )
            
            return {
                "document_id": document_id,
                "document_name": document.name,
                "document_type": document_type,
                "parse_status": document.parse_status,
                "parse_result": parse_result
            }
            
        except Exception as e:
            logger.error(f"Error ensuring document parsed: {str(e)}", exc_info=True)
            
            if trace_id and observability_service and ensure_span_id:
                ensure_duration = (time.time() - ensure_start) * 1000
                observability_service.update_span(
                    span_id=ensure_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=ensure_duration,
                    status_code="ERROR",
                    status_message=str(e)
                )
            
            raise
    
    async def _extract_document_context(
        self,
        document_id: int,
        document_type: str,
        document_info: Dict[str, Any],
        trace_id: Optional[str] = None,
        observability_service: Optional[ObservabilityService] = None,
        parent_span_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract document context based on document type
        
        For API documents: Extract data structure (schema)
        For requirement documents: Extract test points and business rules
        
        Args:
            document_id: Document ID
            document_type: Document type (api, requirement, unknown)
            document_info: Document information dict
            trace_id: Optional trace ID
            observability_service: Optional observability service
            parent_span_id: Optional parent span ID
        
        Returns:
            Document context dict with extracted information
        """
        extract_span_id = None
        extract_start = time.time()
        
        try:
            # Span: Extract document context
            if trace_id and observability_service:
                extract_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="extract_document_context",
                    kind="internal",
                    parent_span_id=parent_span_id,
                    attributes={
                        "document_id": document_id,
                        "document_type": document_type
                    }
                )
                extract_span_id = extract_span.get('data', {}).get('span_id') if extract_span.get('success') else None
            
            parse_result = document_info.get("parse_result", {})
            raw_content = parse_result.get("raw_content", "")
            metadata = parse_result.get("metadata", {})
            
            context = {}
            
            if document_type == "api":
                # Extract data structure for API documents
                logger.info(f"Extracting data structure for API document {document_id}")
                
                # Create span for data structure agent
                structure_span_id = None
                structure_start = None
                if trace_id and observability_service:
                    structure_start = time.time()
                    structure_span = observability_service.create_span(
                        trace_id=trace_id,
                        name="data_structure_agent",
                        kind="agent",
                        parent_span_id=extract_span_id,
                        attributes={
                            "document_id": document_id,
                            "document_content_preview": raw_content[:500] if raw_content else "",
                            "document_content_length": len(raw_content) if raw_content else 0,
                            "has_metadata": bool(metadata)
                        }
                    )
                    structure_span_id = structure_span.get('data', {}).get('span_id') if structure_span.get('success') else None
                
                try:
                    structure_agent = DataStructureAgent(model_config_dict=self.model_config_dict, db=self.db)
                    structure_result = await structure_agent.extract_data_structure(
                        document_content=raw_content,
                        document_metadata=metadata
                    )
                    
                    # Update span with output
                    if trace_id and observability_service and structure_span_id and structure_start is not None:
                        structure_duration = (time.time() - structure_start) * 1000
                        fields = structure_result.get("fields", [])
                        schema = structure_result.get("schema", {})
                        examples = structure_result.get("examples", [])
                        
                        # Prepare schema preview
                        schema_preview = ""
                        if schema:
                            import json
                            try:
                                schema_str = json.dumps(schema, ensure_ascii=False)
                                schema_preview = schema_str[:500]
                            except:
                                schema_preview = str(schema)[:500]
                        
                        observability_service.update_span(
                            span_id=structure_span_id,
                            end_time=datetime.utcnow(),
                            duration_ms=structure_duration,
                            status_code="OK",
                            attributes={
                                "fields_count": len(fields),
                                "has_schema": bool(schema),
                                "schema_type": schema.get("type", "") if schema else "",
                                "has_examples": bool(examples),
                                "examples_count": len(examples) if examples else 0,
                                "schema_preview": schema_preview
                            }
                        )
                    
                    context = {
                        "context_type": "schema",
                        "schema": structure_result.get("schema", {}),
                        "fields": structure_result.get("fields", []),
                        "examples": structure_result.get("examples", [])
                    }
                except Exception as e:
                    logger.error(f"Error in data structure agent for document {document_id}: {str(e)}", exc_info=True)
                    # Update span with error
                    if trace_id and observability_service and structure_span_id and structure_start is not None:
                        structure_duration = (time.time() - structure_start) * 1000
                        observability_service.update_span(
                            span_id=structure_span_id,
                            end_time=datetime.utcnow(),
                            duration_ms=structure_duration,
                            status_code="ERROR",
                            status_message=str(e)
                        )
                    # Re-raise to be caught by outer exception handler
                    raise
                
            elif document_type == "requirement":
                # Extract test points for requirement documents
                logger.info(f"Extracting test points for requirement document {document_id}")
                
                # Create span for test point agent
                test_point_span_id = None
                test_point_start = None
                if trace_id and observability_service:
                    test_point_start = time.time()
                    test_point_span = observability_service.create_span(
                        trace_id=trace_id,
                        name="test_point_agent",
                        kind="agent",
                        parent_span_id=extract_span_id,
                        attributes={
                            "document_id": document_id,
                            "document_content_preview": raw_content[:500] if raw_content else "",
                            "document_content_length": len(raw_content) if raw_content else 0,
                            "has_metadata": bool(metadata)
                        }
                    )
                    test_point_span_id = test_point_span.get('data', {}).get('span_id') if test_point_span.get('success') else None
                
                try:
                    test_point_agent = TestPointAgent(model_config_dict=self.model_config_dict, db=self.db)
                    test_points_result = await test_point_agent.extract_test_points(
                        document_content=raw_content,
                        document_metadata=metadata
                    )
                    
                    # Extract results
                    test_points = test_points_result.get("test_points", [])
                    entities = test_points_result.get("entities", [])
                    business_rules = test_points_result.get("business_rules", [])
                    
                    # Update span with output
                    if trace_id and observability_service and test_point_span_id and test_point_start is not None:
                        test_point_duration = (time.time() - test_point_start) * 1000
                        
                        # Prepare test points preview
                        test_points_preview = []
                        for scenario in test_points[:3]:
                            scenario_name = scenario.get("scenario", scenario.get("description", "场景"))
                            test_points_preview.append(scenario_name)
                        
                        # Check if results are empty
                        is_empty = not test_points and not entities and not business_rules
                        
                        span_attributes = {
                            "test_points_count": len(test_points),
                            "entities_count": len(entities),
                            "business_rules_count": len(business_rules),
                            "test_points_preview": ", ".join(test_points_preview) if test_points_preview else ""
                        }
                        
                        if is_empty:
                            span_attributes["fallback_reason"] = "Empty results from TestPointAgent, using raw_content"
                            logger.warning(f"TestPointAgent returned empty results for document {document_id}, falling back to raw_content")
                        
                        observability_service.update_span(
                            span_id=test_point_span_id,
                            end_time=datetime.utcnow(),
                            duration_ms=test_point_duration,
                            status_code="OK",
                            attributes=span_attributes
                        )
                    
                    # Check if results are empty and fallback to raw_content
                    if not test_points and not entities and not business_rules:
                        logger.warning(f"TestPointAgent returned empty results for document {document_id}, falling back to raw_content")
                        # Fallback to raw_content
                        context = {
                            "context_type": "raw_content",
                            "raw_content": raw_content[:2000]  # Limit to 2000 chars
                        }
                    else:
                        context = {
                            "context_type": "test_points",
                            "test_points": test_points,
                            "entities": entities,
                            "business_rules": business_rules,
                            "raw_content": raw_content[:2000]  # Also include raw_content as fallback option
                        }
                except Exception as e:
                    logger.error(f"Error in test point agent for document {document_id}: {str(e)}", exc_info=True)
                    # Update span with error
                    if trace_id and observability_service and test_point_span_id and test_point_start is not None:
                        test_point_duration = (time.time() - test_point_start) * 1000
                        observability_service.update_span(
                            span_id=test_point_span_id,
                            end_time=datetime.utcnow(),
                            duration_ms=test_point_duration,
                            status_code="ERROR",
                            status_message=str(e)
                        )
                    # Re-raise to be caught by outer exception handler
                    raise
                
            else:
                # Unknown document type - use raw content as context
                logger.warning(f"Unknown document type for {document_id}, using raw content as context")
                context = {
                    "context_type": "raw_content",
                    "raw_content": raw_content[:2000]  # Limit to 2000 chars
                }
            
            # Update span
            if trace_id and observability_service and extract_span_id:
                extract_duration = (time.time() - extract_start) * 1000
                observability_service.update_span(
                    span_id=extract_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=extract_duration,
                    status_code="OK",
                    attributes={
                        "context_type": context.get("context_type"),
                        "has_schema": "schema" in context,
                        "has_test_points": "test_points" in context
                    }
                )
            
            return context
            
        except Exception as e:
            logger.error(f"Error extracting document context: {str(e)}", exc_info=True)
            
            if trace_id and observability_service and extract_span_id:
                extract_duration = (time.time() - extract_start) * 1000
                observability_service.update_span(
                    span_id=extract_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=extract_duration,
                    status_code="ERROR",
                    status_message=str(e)
                )
            
            # Return empty context on error
            return {
                "context_type": "error",
                "error": str(e)
            }
    
    async def process_multiple_documents(
        self,
        document_ids: List[int],
        user_query: str,
        format_hint: Optional[str] = None,
        trace_id: Optional[str] = None,
        observability_service: Optional[ObservabilityService] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents and merge their contexts
        
        Args:
            document_ids: List of document IDs
            user_query: User's natural language query
            format_hint: Optional format hint
            trace_id: Optional trace ID
            observability_service: Optional observability service
        
        Returns:
            Dict with generated data and merged context
        """
        import asyncio
        
        workflow_start_time = time.time()
        workflow_span_id = None
        
        try:
            # Span: Multiple documents workflow
            if trace_id and observability_service:
                workflow_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="multiple_documents_workflow",
                    kind="internal",
                    attributes={
                        "document_ids": document_ids,
                        "document_count": len(document_ids),
                        "user_query": user_query,
                        "format_hint": format_hint
                    }
                )
                workflow_span_id = workflow_span.get('data', {}).get('span_id') if workflow_span.get('success') else None
            
            # Step 1: Process all documents in parallel
            logger.info(f"Processing {len(document_ids)} documents in parallel")
            
            # Create tasks for all documents
            tasks = []
            for doc_id in document_ids:
                task = self._process_single_document_for_merge(
                    doc_id, trace_id, observability_service, workflow_span_id
                )
                tasks.append(task)
            
            # Wait for all documents to be processed
            document_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Step 2: Group documents by type and merge contexts
            api_docs = []
            requirement_docs = []
            unknown_docs = []
            
            for i, result in enumerate(document_results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing document {document_ids[i]}: {result}")
                    continue
                
                doc_id = document_ids[i]
                doc_type = result.get("document_type", "unknown")
                doc_context = result.get("document_context", {})
                
                if doc_type == "api":
                    api_docs.append({
                        "document_id": doc_id,
                        "document_name": result.get("document_name", ""),
                        "context": doc_context
                    })
                elif doc_type == "requirement":
                    requirement_docs.append({
                        "document_id": doc_id,
                        "document_name": result.get("document_name", ""),
                        "context": doc_context
                    })
                else:
                    unknown_docs.append({
                        "document_id": doc_id,
                        "document_name": result.get("document_name", ""),
                        "context": doc_context
                    })
            
            # Step 3: Merge contexts
            merged_context = self._merge_document_contexts(api_docs, requirement_docs, unknown_docs)
            
            # Step 4: Enhance user query with merged context
            enhanced_query = self._enhance_query_with_merged_context(user_query, merged_context)
            
            # Step 5: Generate data using enhanced query
            data_generation_agent = DataGenerationAgent(self.model_config_dict)
            generated_content, usage = await data_generation_agent.generate_data(
                user_query=enhanced_query,
                format_hint=format_hint,
                trace_id=trace_id,
                observability_service=observability_service
            )
            
            # Step 6: Update workflow span
            if trace_id and observability_service and workflow_span_id:
                workflow_duration = (time.time() - workflow_start_time) * 1000
                observability_service.update_span(
                    span_id=workflow_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=workflow_duration,
                    status_code="OK",
                    attributes={
                        "api_docs_count": len(api_docs),
                        "requirement_docs_count": len(requirement_docs),
                        "unknown_docs_count": len(unknown_docs),
                        "context_type": merged_context.get("context_type"),
                        "usage": usage
                    }
                )
            
            return {
                "success": True,
                "generated_data": generated_content,
                "format": format_hint or "json",
                "usage": usage,
                "workflow_metadata": {
                    "document_ids": document_ids,
                    "api_docs_count": len(api_docs),
                    "requirement_docs_count": len(requirement_docs),
                    "unknown_docs_count": len(unknown_docs),
                    "context_extracted": bool(merged_context),
                    "context_type": merged_context.get("context_type") if merged_context else None
                },
                "document_context": merged_context
            }
            
        except Exception as e:
            logger.error(f"Error in multiple documents workflow: {str(e)}", exc_info=True)
            
            if trace_id and observability_service and workflow_span_id:
                workflow_duration = (time.time() - workflow_start_time) * 1000
                observability_service.update_span(
                    span_id=workflow_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=workflow_duration,
                    status_code="ERROR",
                    status_message=str(e)
                )
            
            raise
    
    async def _process_single_document_for_merge(
        self,
        document_id: int,
        trace_id: Optional[str] = None,
        observability_service: Optional[ObservabilityService] = None,
        parent_span_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single document for merging (internal helper)
        
        Args:
            document_id: Document ID
            trace_id: Optional trace ID
            observability_service: Optional observability service
            parent_span_id: Optional parent span ID
        
        Returns:
            Dict with document info and context
        """
        try:
            # Ensure document is parsed
            document_info = await self._ensure_document_parsed(
                document_id, trace_id, observability_service, parent_span_id
            )
            document_type = document_info.get("document_type", "unknown")
            
            # Extract document context
            document_context = await self._extract_document_context(
                document_id,
                document_type,
                document_info,
                trace_id,
                observability_service,
                parent_span_id
            )
            
            return {
                "document_id": document_id,
                "document_name": document_info.get("document_name", ""),
                "document_type": document_type,
                "document_context": document_context
            }
        except Exception as e:
            logger.error(f"Error processing document {document_id} for merge: {str(e)}", exc_info=True)
            raise
    
    def _merge_document_contexts(
        self,
        api_docs: List[Dict[str, Any]],
        requirement_docs: List[Dict[str, Any]],
        unknown_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge contexts from multiple documents
        
        Args:
            api_docs: List of API document contexts
            requirement_docs: List of requirement document contexts
            unknown_docs: List of unknown document contexts
        
        Returns:
            Merged context dict
        """
        merged = {
            "context_type": "mixed",
            "has_api_context": False,
            "has_requirement_context": False
        }
        
        # Merge API document schemas
        if api_docs:
            merged["has_api_context"] = True
            all_fields = []
            all_schemas = []
            all_examples = []
            field_map = {}  # For deduplication
            
            for doc in api_docs:
                context = doc.get("context", {})
                if context.get("context_type") == "schema":
                    fields = context.get("fields", [])
                    schema = context.get("schema", {})
                    examples = context.get("examples", [])
                    
                    # Merge fields with deduplication
                    for field in fields:
                        field_name = field.get("name", "")
                        if field_name in field_map:
                            # Merge field constraints (take stricter ones)
                            existing = field_map[field_name]
                            # Update with stricter constraints
                            if field.get("required", False) and not existing.get("required", False):
                                existing["required"] = True
                            # Merge other constraints
                            for key in ["minLength", "maxLength", "minimum", "maximum"]:
                                if key in field.get("constraints", {}):
                                    existing_constraint = existing.get("constraints", {}).get(key)
                                    field_constraint = field.get("constraints", {}).get(key)
                                    if existing_constraint is None or (
                                        key in ["minLength", "minimum"] and field_constraint > existing_constraint
                                    ) or (
                                        key in ["maxLength", "maximum"] and field_constraint < existing_constraint
                                    ):
                                        if "constraints" not in existing:
                                            existing["constraints"] = {}
                                        existing["constraints"][key] = field_constraint
                        else:
                            field_map[field_name] = field.copy()
                    
                    all_schemas.append(schema)
                    all_examples.extend(examples)
            
            merged["api_context"] = {
                "fields": list(field_map.values()),
                "schemas": all_schemas,
                "examples": all_examples[:5]  # Limit examples
            }
        
        # Merge requirement document test points
        if requirement_docs:
            merged["has_requirement_context"] = True
            all_test_points = []
            all_entities = []
            all_business_rules = []
            entity_map = {}  # For deduplication
            
            for doc in requirement_docs:
                context = doc.get("context", {})
                if context.get("context_type") == "test_points":
                    test_points = context.get("test_points", [])
                    entities = context.get("entities", [])
                    business_rules = context.get("business_rules", [])
                    
                    all_test_points.extend(test_points)
                    
                    # Merge entities with deduplication
                    for entity in entities:
                        entity_name = entity.get("name", "")
                        if entity_name not in entity_map:
                            entity_map[entity_name] = entity.copy()
                        else:
                            # Merge entity fields
                            existing_fields = entity_map[entity_name].get("fields", [])
                            new_fields = entity.get("fields", [])
                            field_names = {f.get("name", "") for f in existing_fields}
                            for field in new_fields:
                                if field.get("name", "") not in field_names:
                                    existing_fields.append(field)
                    
                    all_business_rules.extend(business_rules)
                elif context.get("context_type") == "raw_content":
                    # Include raw content for fallback
                    if "raw_content" not in merged:
                        merged["raw_content"] = []
                    merged["raw_content"].append(context.get("raw_content", ""))
            
            merged["requirement_context"] = {
                "test_points": all_test_points[:10],  # Limit test points
                "entities": list(entity_map.values()),
                "business_rules": all_business_rules[:20]  # Limit business rules
            }
        
        # Handle unknown documents
        if unknown_docs:
            raw_contents = []
            for doc in unknown_docs:
                context = doc.get("context", {})
                if context.get("context_type") == "raw_content":
                    raw_contents.append(context.get("raw_content", ""))
            if raw_contents:
                if "raw_content" not in merged:
                    merged["raw_content"] = []
                merged["raw_content"].extend(raw_contents)
        
        return merged
    
    def _enhance_query_with_merged_context(
        self,
        user_query: str,
        merged_context: Dict[str, Any]
    ) -> str:
        """
        Enhance user query with merged context from multiple documents
        
        Args:
            user_query: Original user query
            merged_context: Merged context from multiple documents
        
        Returns:
            Enhanced query string
        """
        enhanced = f"{user_query}\n\n"
        
        # Add API context if available
        if merged_context.get("has_api_context"):
            api_context = merged_context.get("api_context", {})
            fields = api_context.get("fields", [])
            schemas = api_context.get("schemas", [])
            
            enhanced += "## 接口文档字段结构\n\n"
            enhanced += f"字段定义（共{len(fields)}个字段）：\n"
            
            for field in fields[:20]:  # Limit to 20 fields
                field_info = f"- {field.get('name', 'unknown')}: {field.get('type', 'unknown')}"
                if field.get('description'):
                    field_info += f" - {field.get('description')}"
                if field.get('required'):
                    field_info += " [必填]"
                enhanced += field_info + "\n"
            
            if len(fields) > 20:
                enhanced += f"\n[还有 {len(fields) - 20} 个字段未显示]\n"
            
            # Add first schema if available
            if schemas and len(schemas) > 0:
                import json
                schema_str = json.dumps(schemas[0], ensure_ascii=False, indent=2)
                enhanced += f"\nJSON Schema:\n```json\n{schema_str}\n```\n"
            
            enhanced += "\n"
        
        # Add requirement context if available
        if merged_context.get("has_requirement_context"):
            req_context = merged_context.get("requirement_context", {})
            entities = req_context.get("entities", [])
            business_rules = req_context.get("business_rules", [])
            test_points = req_context.get("test_points", [])
            
            enhanced += "## 需求文档测试点和业务规则\n\n"
            
            if entities:
                enhanced += f"业务实体（共{len(entities)}个）：\n"
                for entity in entities[:5]:  # Limit to 5 entities
                    entity_name = entity.get("name", "unknown")
                    entity_fields = entity.get("fields", [])
                    enhanced += f"- {entity_name}: {len(entity_fields)}个字段\n"
                enhanced += "\n"
            
            if business_rules:
                enhanced += f"业务规则（共{len(business_rules)}条）：\n"
                for rule in business_rules[:10]:  # Limit to 10 rules
                    rule_name = rule.get("rule_name", rule.get("description", "规则"))
                    enhanced += f"- {rule_name}\n"
                enhanced += "\n"
            
            if test_points:
                enhanced += f"测试场景（共{len(test_points)}个）：\n"
                for scenario in test_points[:3]:  # Limit to 3 scenarios
                    scenario_name = scenario.get("scenario", scenario.get("description", "场景"))
                    enhanced += f"- {scenario_name}\n"
                enhanced += "\n"
        
        # Add instruction
        if merged_context.get("has_api_context") and merged_context.get("has_requirement_context"):
            enhanced += "请根据以上接口文档的字段结构和需求文档的测试点、业务规则生成符合要求的测试数据。"
        elif merged_context.get("has_api_context"):
            enhanced += "请严格遵循以上字段定义和约束条件生成数据。"
        elif merged_context.get("has_requirement_context"):
            enhanced += "请根据以上业务实体、规则和测试场景生成符合要求的测试数据。"
        else:
            # Fallback to raw content if available
            raw_contents = merged_context.get("raw_content", [])
            if raw_contents:
                enhanced += "参考文档内容：\n"
                for content in raw_contents[:2]:  # Limit to 2 raw contents
                    enhanced += f"{content[:1000]}\n\n"  # Limit each to 1000 chars
                enhanced += "请根据文档内容生成数据。"
            else:
                # No context available, use original query
                enhanced = user_query
        
        return enhanced
    
    def _enhance_query_with_context(
        self,
        user_query: str,
        document_context: Dict[str, Any],
        document_type: str
    ) -> str:
        """
        Enhance user query with document context
        
        Args:
            user_query: Original user query
            document_context: Extracted document context
            document_type: Document type
        
        Returns:
            Enhanced query string
        """
        context_type = document_context.get("context_type", "")
        
        if context_type == "schema":
            # Enhance with schema information
            schema = document_context.get("schema", {})
            fields = document_context.get("fields", [])
            
            enhanced = f"{user_query}\n\n"
            enhanced += "请根据以下接口文档的字段结构生成数据：\n\n"
            enhanced += f"字段定义（共{len(fields)}个字段）：\n"
            
            for field in fields[:20]:  # Limit to 20 fields to avoid token limits
                field_info = f"- {field.get('name', 'unknown')}: {field.get('type', 'unknown')}"
                if field.get('description'):
                    field_info += f" - {field.get('description')}"
                if field.get('required'):
                    field_info += " [必填]"
                enhanced += field_info + "\n"
            
            if len(fields) > 20:
                enhanced += f"\n[还有 {len(fields) - 20} 个字段未显示]\n"
            
            # Add schema JSON if available
            if schema:
                import json
                schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
                enhanced += f"\nJSON Schema:\n```json\n{schema_str}\n```\n"
            
            enhanced += "\n请严格遵循以上字段定义和约束条件生成数据。"
            
        elif context_type == "test_points":
            # Enhance with test points and business rules
            test_points = document_context.get("test_points", [])
            entities = document_context.get("entities", [])
            business_rules = document_context.get("business_rules", [])
            
            # If all results are empty, fallback to raw_content
            if not test_points and not entities and not business_rules:
                raw_content = document_context.get("raw_content", "")
                if raw_content:
                    logger.warning("All test_points results are empty, falling back to raw_content in query enhancement")
                    enhanced = f"{user_query}\n\n参考文档内容：\n{raw_content}\n\n请根据文档内容生成数据。"
                else:
                    # If raw_content is also not available, use original query
                    logger.warning("All test_points results are empty and raw_content is not available, using original query")
                    enhanced = user_query
            else:
                enhanced = f"{user_query}\n\n"
                enhanced += "请根据以下需求文档的测试点和业务规则生成数据：\n\n"
                
                if entities:
                    enhanced += f"业务实体（共{len(entities)}个）：\n"
                    for entity in entities[:5]:  # Limit to 5 entities
                        entity_name = entity.get("name", "unknown")
                        entity_fields = entity.get("fields", [])
                        enhanced += f"- {entity_name}: {len(entity_fields)}个字段\n"
                    enhanced += "\n"
                
                if business_rules:
                    enhanced += f"业务规则（共{len(business_rules)}条）：\n"
                    for rule in business_rules[:10]:  # Limit to 10 rules
                        rule_name = rule.get("rule_name", rule.get("description", "规则"))
                        enhanced += f"- {rule_name}\n"
                    enhanced += "\n"
                
                if test_points:
                    enhanced += f"测试场景（共{len(test_points)}个）：\n"
                    for scenario in test_points[:3]:  # Limit to 3 scenarios
                        scenario_name = scenario.get("scenario", scenario.get("description", "场景"))
                        enhanced += f"- {scenario_name}\n"
                    enhanced += "\n"
                
                enhanced += "请根据以上业务实体、规则和测试场景生成符合要求的测试数据。"
            
        else:
            # Use raw content or no enhancement
            if context_type == "raw_content":
                raw_content = document_context.get("raw_content", "")
                enhanced = f"{user_query}\n\n参考文档内容：\n{raw_content}\n\n请根据文档内容生成数据。"
            else:
                # No context available, use original query
                enhanced = user_query
        
        return enhanced
