"""
Data generation API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from app.core.database import get_db
from app.api.v1.schemas import DocumentReference, DataGenerationRequest
from app.services.llm_service import DataGenerationAgent
from app.services.model_config_service import ModelConfigService
from app.services.data_parser import DataParser
from app.services.format_converter import FormatConverter
from app.services.generation_history_service import GenerationHistoryService
from app.services.observability_service import ObservabilityService
from app.services.workflow_router import WorkflowRouter
from app.services.document_workflow_processor import DocumentWorkflowProcessor
from app.services.template_workflow_processor import TemplateWorkflowProcessor
from app.services.data_validator import DataValidator
from app.services.user_intent_service import UserIntentService
from app.utils.api_decorators import handle_api_errors
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=Dict[str, Any])
@handle_api_errors
async def generate_data(
    request: DataGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Generate test data based on user query
    
    Args:
        request: Data generation request with user query
        db: Database session
    
    Returns:
        Generated data with format and usage information
    """
    try:
        trace_id = None
        trace_start_time = time.time()
        observability_service = ObservabilityService(db)
        
        # Create trace for observability
        trace_result = observability_service.create_trace(
            service_name="DataGenAgent",
            operation_name="generate_data",
            attributes={
                "user_query": request.user_query,
                "format": request.format,
                "model_config_id": request.model_config_id,
            }
        )
        if trace_result.get('success'):
            trace_id = trace_result['data']['trace_id']
            # 验证 trace 是否真的创建成功
            verify_trace = observability_service.get_trace_by_id(trace_id)
            if not verify_trace:
                logger.warning(f"Trace created but not found in database: {trace_id}")
                trace_id = None  # 重置 trace_id，避免后续操作使用无效的 trace_id
            else:
                logger.info(f"Trace created successfully: {trace_id}")
        else:
            logger.warning(f"Failed to create trace: {trace_result.get('message', 'Unknown error')}")
            trace_id = None
        
        # Get model configuration
        model_config_service = ModelConfigService(db)
        
        if request.model_config_id:
            model_config_dict = model_config_service.get_config_dict_for_llm(request.model_config_id)
            if not model_config_dict:
                raise HTTPException(status_code=404, detail="Model configuration not found")
        else:
            # Use default model config
            default_config = model_config_service.get_default_config(include_sensitive=True)
            if not default_config:
                raise HTTPException(
                    status_code=400, 
                    detail="No model configuration found. Please configure a model first."
                )
            model_config_dict = model_config_service.get_config_dict_for_llm(default_config['id'])
        
        # User intent recognition: check if query is data-related or chat
        intent_span_id = None
        if trace_id:
            intent_span = observability_service.create_span(
                trace_id=trace_id,
                name="user_intent_recognition",
                kind="internal",
                attributes={
                    "user_query": request.user_query
                }
            )
            intent_span_id = intent_span.get('data', {}).get('span_id') if intent_span.get('success') else None
            intent_start = time.time()
        
        try:
            intent_service = UserIntentService(model_config_dict=model_config_dict)
            intent_result = await intent_service.recognize_intent(request.user_query)
            intent_type = intent_result.get("intent_type", "data_related")
            intent_confidence = intent_result.get("confidence", 0.0)
            intent_reasoning = intent_result.get("reasoning", "")
            
            # Log intent recognition result
            logger.info(f"User intent recognized: {intent_type} (confidence: {intent_confidence})")
            
            # Update intent span with result
            if trace_id and intent_span_id:
                intent_duration = (time.time() - intent_start) * 1000
                observability_service.update_span(
                    span_id=intent_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=intent_duration,
                    status_code="OK",
                    attributes={
                        "intent_type": intent_type,
                        "confidence": intent_confidence,
                        "reasoning": intent_reasoning
                    }
                )
            
            # If intent is chat, return fallback message
            if intent_type == "chat":
                logger.info(f"Chat intent detected, returning fallback message")
                return {
                    "success": False,
                    "message": "抱歉，我目前专注于数据生成和数据分析相关的问题，暂不支持其他类型的咨询。请提出与数据生成或数据分析相关的问题。",
                    "intent_type": "chat",
                    "intent_confidence": intent_confidence
                }
        except Exception as e:
            # If intent recognition fails, log error but continue processing (lenient policy)
            logger.warning(f"User intent recognition failed: {str(e)}, continuing with normal processing")
            if trace_id and intent_span_id:
                intent_duration = (time.time() - intent_start) * 1000
                observability_service.update_span(
                    span_id=intent_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=intent_duration,
                    status_code="ERROR",
                    attributes={
                        "error": str(e),
                        "fallback": "continuing_with_normal_processing"
                    }
                )
            # Continue with normal processing to avoid blocking valid requests
        
        # Check if workflow processing is needed
        workflow_router = WorkflowRouter()
        parsed_refs = workflow_router.parse_references(request.user_query, request.references)
        
        # Validate: template and document are mutually exclusive
        if parsed_refs["has_template_refs"] and parsed_refs["has_document_refs"]:
            raise HTTPException(
                status_code=400,
                detail="模版类型和文档类型只能选择一类，请移除其中一类引用"
            )
        
        workflow_type = workflow_router.route_to_workflow(parsed_info=parsed_refs)
        
        generated_content = None
        usage = {}
        workflow_metadata = {}
        validation_result = None
        
        # Route to appropriate workflow
        if workflow_type == "mixed" and (parsed_refs["has_template_refs"] or parsed_refs["has_document_refs"]):
            # Mixed workflow: template + document
            logger.info(f"Routing to mixed workflow (template + document)")
            
            # Get template and document references
            template_refs = workflow_router.get_template_references(parsed_refs["references"])
            document_refs = workflow_router.get_document_references(parsed_refs["references"])
            
            if not template_refs:
                raise HTTPException(status_code=400, detail="No valid template references found")
            
            # Process document first to get document context
            document_context = None
            if document_refs:
                document_id = document_refs[0].id
                doc_processor = DocumentWorkflowProcessor(db, model_config_dict)
                doc_result = await doc_processor.process_document_workflow(
                    document_id=document_id,
                    user_query=request.user_query,
                    format_hint=request.format,
                    trace_id=trace_id,
                    observability_service=observability_service
                )
                if doc_result.get("success"):
                    document_context = doc_result.get("document_context")
            
            # Create template workflow processor
            template_processor = TemplateWorkflowProcessor(db, model_config_dict)
            
            # Process template workflow with document context
            workflow_result = await template_processor.process_template_workflow(
                template_refs=template_refs,
                user_query=request.user_query,
                format_hint=request.format,
                document_refs=document_refs,
                document_context=document_context,
                trace_id=trace_id,
                observability_service=observability_service
            )
            
            if not workflow_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Template workflow failed: {workflow_result.get('error', 'Unknown error')}"
                )
            
            generated_content = workflow_result.get("generated_data", "")
            usage = workflow_result.get("usage", {})
            workflow_metadata = workflow_result.get("workflow_metadata", {})
            template_context = workflow_result.get("template_context", {})
            
            # Validate generated data if schema is available
            if template_context.get("context_type") == "schema":
                schema = template_context.get("schema")
                if schema:
                    parsed_data = DataParser.parse_generated_data(
                        content=generated_content,
                        format=request.format
                    )
                    validator = DataValidator()
                    validation_result = validator.validate_against_schema(parsed_data, schema)
                    if not validation_result.get("valid"):
                        logger.warning(f"Generated data validation failed: {validation_result.get('errors', [])}")
        
        elif workflow_type == "template" and parsed_refs["has_template_refs"]:
            # Template workflow: process template-based generation
            logger.info(f"Routing to template workflow for {len(parsed_refs['references'])} template(s)")
            
            # Get template references
            template_refs = workflow_router.get_template_references(parsed_refs["references"])
            if not template_refs:
                raise HTTPException(status_code=400, detail="No valid template references found")
            
            # Create template workflow processor
            template_processor = TemplateWorkflowProcessor(db, model_config_dict)
            
            # Process template workflow
            workflow_result = await template_processor.process_template_workflow(
                template_refs=template_refs,
                user_query=request.user_query,
                format_hint=request.format,
                trace_id=trace_id,
                observability_service=observability_service
            )
            
            if not workflow_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Template workflow failed: {workflow_result.get('error', 'Unknown error')}"
                )
            
            generated_content = workflow_result.get("generated_data", "")
            usage = workflow_result.get("usage", {})
            workflow_metadata = workflow_result.get("workflow_metadata", {})
            template_context = workflow_result.get("template_context", {})
            
            # Validate generated data if schema is available
            if template_context.get("context_type") == "schema":
                schema = template_context.get("schema")
                if schema:
                    parsed_data = DataParser.parse_generated_data(
                        content=generated_content,
                        format=request.format
                    )
                    validator = DataValidator()
                    validation_result = validator.validate_against_schema(parsed_data, schema)
                    if not validation_result.get("valid"):
                        logger.warning(f"Generated data validation failed: {validation_result.get('errors', [])}")
        
        elif workflow_type == "document" and parsed_refs["has_document_refs"]:
            # Document workflow: process document-based generation
            logger.info(f"Routing to document workflow for {len(parsed_refs['references'])} document(s)")
            
            # Get document references
            document_refs = workflow_router.get_document_references(parsed_refs["references"])
            if not document_refs:
                raise HTTPException(status_code=400, detail="No valid document references found")
            
            # Create document workflow processor
            workflow_processor = DocumentWorkflowProcessor(db, model_config_dict)
            
            # Process single or multiple documents
            if len(document_refs) == 1:
                # Single document: use existing method
                document_id = document_refs[0].id
                workflow_result = await workflow_processor.process_document_workflow(
                    document_id=document_id,
                    user_query=request.user_query,
                    format_hint=request.format,
                    trace_id=trace_id,
                    observability_service=observability_service
                )
            else:
                # Multiple documents: use new method
                document_ids = [ref.id for ref in document_refs]
                workflow_result = await workflow_processor.process_multiple_documents(
                    document_ids=document_ids,
                    user_query=request.user_query,
                    format_hint=request.format,
                    trace_id=trace_id,
                    observability_service=observability_service
                )
            
            if not workflow_result.get("success"):
                raise HTTPException(
                    status_code=500, 
                    detail=f"Document workflow failed: {workflow_result.get('error', 'Unknown error')}"
                )
            
            generated_content = workflow_result.get("generated_data", "")
            usage = workflow_result.get("usage", {})
            workflow_metadata = workflow_result.get("workflow_metadata", {})
            document_context = workflow_result.get("document_context", {})
            
            # Validate generated data if schema is available
            # For multiple documents, check if merged context has schema
            if document_context.get("has_api_context"):
                api_context = document_context.get("api_context", {})
                schemas = api_context.get("schemas", [])
                if schemas and len(schemas) > 0:
                    schema = schemas[0]  # Use first schema for validation
                    # Parse generated data for validation
                    parsed_data = DataParser.parse_generated_data(
                        content=generated_content,
                        format=request.format
                    )
                    
                    # Validate against schema
                    validator = DataValidator()
                    validation_result = validator.validate_against_schema(parsed_data, schema)
                    
                    if not validation_result.get("valid"):
                        logger.warning(f"Generated data validation failed: {validation_result.get('errors', [])}")
                        # Continue even if validation fails, but log the errors
            elif workflow_metadata.get("document_type") == "api" and document_context.get("context_type") == "schema":
                # Single document with schema
                schema = document_context.get("schema")
                if schema:
                    # Parse generated data for validation
                    parsed_data = DataParser.parse_generated_data(
                        content=generated_content,
                        format=request.format
                    )
                    
                    # Validate against schema
                    validator = DataValidator()
                    validation_result = validator.validate_against_schema(parsed_data, schema)
                    
                    if not validation_result.get("valid"):
                        logger.warning(f"Generated data validation failed: {validation_result.get('errors', [])}")
                        # Continue even if validation fails, but log the errors
        
        else:
            # Default text workflow: use original data generation
            logger.info("Using default text workflow")
            
            # Create data generation agent
            agent = DataGenerationAgent(model_config_dict)
            
            # Generate data with trace support
            try:
                generated_content, usage = await agent.generate_data(
                    user_query=request.user_query,
                    format_hint=request.format,
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
        
        # Span: Parse generated data
        parse_span_id = None
        if trace_id:
            parse_span = observability_service.create_span(
                trace_id=trace_id,
                name="parse_data",
                kind="internal",
                attributes={
                    "format": request.format,
                    "content_length": len(generated_content)
                }
            )
            parse_span_id = parse_span.get('data', {}).get('span_id') if parse_span.get('success') else None
            parse_start = time.time()
        
        # Parse generated data
        parsed_data = DataParser.parse_generated_data(
            content=generated_content,
            format=request.format
        )
        
        if trace_id and parse_span_id:
            parse_duration = (time.time() - parse_start) * 1000
            observability_service.update_span(
                span_id=parse_span_id,
                end_time=datetime.utcnow(),
                duration_ms=parse_duration,
                status_code="OK",
                events=[{
                    "name": "parse_complete",
                    "timestamp": datetime.utcnow().isoformat(),
                    "attributes": {
                        "parsed_type": type(parsed_data).__name__,
                        "is_list": isinstance(parsed_data, list),
                        "list_length": len(parsed_data) if isinstance(parsed_data, list) else None
                    }
                }]
            )
        
        # Span: Format data
        format_span_id = None
        if trace_id:
            format_span = observability_service.create_span(
                trace_id=trace_id,
                name="format_data",
                kind="internal",
                attributes={
                    "requested_format": request.format
                }
            )
            format_span_id = format_span.get('data', {}).get('span_id') if format_span.get('success') else None
            format_start = time.time()
        
        # Convert to requested format if needed
        final_format = request.format or DataParser.detect_format(generated_content)
        if final_format == "json":
            formatted_data = FormatConverter.convert_to_json(parsed_data)
        elif final_format == "csv":
            # Ensure parsed_data is list of dicts for CSV conversion
            if isinstance(parsed_data, list):
                formatted_data = FormatConverter.convert_to_csv(parsed_data)
            else:
                formatted_data = generated_content  # Use original if conversion fails
        elif final_format == "excel":
            # Ensure parsed_data is list of dicts for Excel conversion
            if isinstance(parsed_data, list):
                excel_bytes = FormatConverter.convert_to_excel(parsed_data)
                # For Excel, we'll return base64 encoded bytes
                import base64
                formatted_data = base64.b64encode(excel_bytes).decode('utf-8')
            else:
                formatted_data = generated_content
        else:
            formatted_data = str(parsed_data) if not isinstance(parsed_data, str) else parsed_data
        
        if trace_id and format_span_id:
            format_duration = (time.time() - format_start) * 1000
            observability_service.update_span(
                span_id=format_span_id,
                end_time=datetime.utcnow(),
                duration_ms=format_duration,
                status_code="OK",
                events=[{
                    "name": "format_complete",
                    "timestamp": datetime.utcnow().isoformat(),
                    "attributes": {
                        "final_format": final_format,
                        "formatted_data_length": len(formatted_data)
                    }
                }]
            )
        
        # Update trace with success
        if trace_id:
            trace_duration = (time.time() - trace_start_time) * 1000
            trace_attributes = {
                "user_query": request.user_query,
                "format": final_format,
                "model_config_id": request.model_config_id,
                "usage": usage,
                "workflow_type": workflow_type,
            }
            
            # Add workflow metadata if available
            if workflow_metadata:
                trace_attributes["workflow_metadata"] = workflow_metadata
            
            # Add validation result if available
            if validation_result:
                trace_attributes["validation_valid"] = validation_result.get("valid", False)
                if not validation_result.get("valid"):
                    trace_attributes["validation_errors"] = validation_result.get("errors", [])
            
            observability_service.update_trace(
                trace_id=trace_id,
                end_time=datetime.utcnow(),
                duration_ms=trace_duration,
                status_code="OK",
                attributes=trace_attributes
            )
        
        # Save to history
        history_service = GenerationHistoryService(db)
        model_name = f"{model_config_dict.get('model_type', 'unknown')}/{model_config_dict.get('model_version', 'unknown')}"
        
        # Determine input type based on references
        input_type = "text"
        if request.references and len(request.references) > 0:
            ref_types = [ref.type for ref in request.references]
            if len(set(ref_types)) > 1:
                input_type = "mixed"
            else:
                input_type = ref_types[0] if ref_types else "text"
        
        # Convert references to dict for storage
        references_data = None
        if request.references:
            references_data = [{"type": ref.type, "id": ref.id, "name": ref.name} for ref in request.references]
        
        history_result = history_service.create_history(
            user_query=request.user_query,
            generated_data=formatted_data,
            data_format=final_format,
            model_used=model_name,
            model_config_id=request.model_config_id,
            input_type=input_type,
            references=references_data
        )
        
        history_id = history_result.get('data', {}).get('id') if history_result.get('success') else None
        
        # Update trace with history_id (merge with existing attributes)
        if trace_id and history_id:
            # Get current trace to merge attributes
            current_trace = observability_service.get_trace_by_id(trace_id)
            if current_trace:
                current_attributes = current_trace.get('attributes', {})
                current_attributes['history_id'] = history_id
                observability_service.update_trace(
                    trace_id=trace_id,
                    attributes=current_attributes
                )
        
        response_data = {
            "generated_data": formatted_data,
            "format": final_format,
            "usage": usage,
            "history_id": history_id,
            "trace_id": trace_id,
        }
        
        # Add workflow metadata if available
        if workflow_metadata:
            response_data["workflow_metadata"] = workflow_metadata
        
        # Add validation result if available
        if validation_result:
            response_data["validation"] = {
                "valid": validation_result.get("valid", False),
                "errors": validation_result.get("errors", []),
                "warnings": validation_result.get("warnings", [])
            }
        
        return {
            "success": True,
            "data": response_data,
            "message": "Data generated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate data: {str(e)}")
