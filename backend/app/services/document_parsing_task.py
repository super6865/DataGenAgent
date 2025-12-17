"""
Asynchronous document parsing task
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.services.document_parser_service import DocumentParserService
from app.agents.intent_recognition_agent import IntentRecognitionAgent
from app.models.document import Document

logger = logging.getLogger(__name__)


class DocumentParsingTask:
    """Task for parsing documents asynchronously"""
    
    def __init__(self, db: Session):
        """
        Initialize document parsing task
        
        Args:
            db: Database session
        """
        self.db = db
        self.document_parser = DocumentParserService()
    
    async def parse_document_content(self, document_id: int) -> Dict[str, Any]:
        """
        Parse document content only (without intent recognition)
        
        This method is used when uploading documents or viewing document list.
        It only extracts and structures the document content.
        
        Workflow:
        1. Update status to "parsing"
        2. Parse document content using MCP or local parser
        3. Update database with parse result (document_type remains None or "unknown")
        
        Args:
            document_id: Document ID to parse
        
        Returns:
            Parsing result dictionary
        """
        try:
            # Get document
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Update status to parsing
            document.parse_status = "parsing"
            self.db.commit()
            logger.info(f"Started parsing document content {document_id}: {document.name}")
            
            # Parse document content
            parse_result = await self.document_parser.parse_document(
                file_path=document.file_path,
                file_type=document.file_type
            )
            
            # Update database with results (without document_type)
            document.parse_status = "success"
            document.parse_result = parse_result
            # Keep document_type as None or existing value (don't set to unknown)
            from datetime import datetime
            document.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Successfully parsed document content {document_id}: {document.name}")
            
            return {
                "success": True,
                "document_id": document_id,
                "parse_result": parse_result,
                "document_type": document.document_type
            }
            
        except Exception as e:
            logger.error(f"Error parsing document content {document_id}: {str(e)}", exc_info=True)
            
            # Update status to failed
            try:
                document = self.db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.parse_status = "failed"
                    from datetime import datetime
                    document.updated_at = datetime.utcnow()
                    self.db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update parse status: {str(update_error)}")
                self.db.rollback()
            
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e)
            }
    
    async def parse_document_with_intent(
        self, 
        document_id: int,
        trace_id: Optional[str] = None,
        observability_service: Optional[Any] = None,
        parent_span_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse document content and recognize document type using Intent Recognition Agent
        
        This method performs both content parsing and intent recognition.
        If intent recognition fails, content parsing still succeeds with document_type="unknown".
        
        Workflow:
        1. Parse document content (if not already parsed)
        2. Recognize document type using Intent Recognition Agent
        3. Update database with results including document_type
        
        Args:
            document_id: Document ID to parse
            trace_id: Optional trace ID for observability
            observability_service: Optional observability service instance
            parent_span_id: Optional parent span ID
        
        Returns:
            Parsing result dictionary with intent recognition
        """
        try:
            # Get document
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Update status to parsing if not already success
            if document.parse_status != "success":
                document.parse_status = "parsing"
                from datetime import datetime
                document.updated_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(document)
                logger.info(f"Started parsing document with intent {document_id}: {document.name}")
            
            # Step 1: Ensure document content is parsed
            if document.parse_status != "success" or not document.parse_result:
                logger.info(f"Document {document_id} not parsed yet, parsing content first...")
                content_result = await self.parse_document_content(document_id)
                if not content_result.get("success"):
                    raise ValueError(f"Failed to parse document content: {content_result.get('error')}")
                # Refresh document to get updated parse_result
                self.db.refresh(document)
            
            parse_result = document.parse_result or {}
            
            # Step 2: Recognize document type using Intent Recognition Agent
            # This step is optional - if it fails, we still mark parsing as successful
            document_type = "unknown"
            intent_span_id = None
            intent_start = None
            
            try:
                # Use raw content for intent recognition
                raw_content = parse_result.get("raw_content", "")
                metadata = parse_result.get("metadata", {})
                
                # Create span for intent recognition agent
                if trace_id and observability_service:
                    intent_start = time.time()
                    intent_span = observability_service.create_span(
                        trace_id=trace_id,
                        name="intent_recognition_agent",
                        kind="agent",
                        parent_span_id=parent_span_id,
                        attributes={
                            "document_id": document_id,
                            "document_content_preview": raw_content[:500] if raw_content else "",
                            "document_content_length": len(raw_content) if raw_content else 0,
                            "has_metadata": bool(metadata),
                            "metadata_title": metadata.get("title", "") if metadata else ""
                        }
                    )
                    intent_span_id = intent_span.get('data', {}).get('span_id') if intent_span.get('success') else None
                
                intent_agent = IntentRecognitionAgent(db=self.db)
                
                # Recognize document type
                intent_result = await intent_agent.recognize_document_type(
                    document_content=raw_content,
                    document_metadata=metadata
                )
                
                document_type = intent_result.get("document_type", "unknown")
                confidence = intent_result.get("confidence", 0.0)
                reasoning = intent_result.get("reasoning", "")
                
                # Update intent recognition span with output
                if trace_id and observability_service and intent_span_id and intent_start is not None:
                    intent_duration = (time.time() - intent_start) * 1000
                    observability_service.update_span(
                        span_id=intent_span_id,
                        end_time=datetime.utcnow(),
                        duration_ms=intent_duration,
                        status_code="OK",
                        attributes={
                            "document_type": document_type,
                            "confidence": float(confidence) if confidence is not None else 0.0,
                            "reasoning_preview": reasoning[:200] if reasoning else "",
                            "reasoning_length": len(reasoning) if reasoning else 0
                        }
                    )
                
                # Add intent recognition result to parse_result
                parse_result["intent_recognition"] = {
                    "document_type": document_type,
                    "confidence": confidence,
                    "reasoning": reasoning
                }
                
                logger.info(
                    f"Document type recognized for {document_id}: {document_type} "
                    f"(confidence: {confidence:.2f})"
                )
                
            except ValueError as e:
                # Model configuration not available - graceful degradation
                logger.warning(f"Intent recognition skipped for document {document_id}: {str(e)}")
                document_type = "unknown"
                parse_result["intent_recognition"] = {
                    "document_type": "unknown",
                    "confidence": 0.0,
                    "reasoning": f"Intent recognition skipped: {str(e)}"
                }
                
                # Update span with error
                if trace_id and observability_service and intent_span_id and intent_start is not None:
                    intent_duration = (time.time() - intent_start) * 1000
                    observability_service.update_span(
                        span_id=intent_span_id,
                        end_time=datetime.utcnow(),
                        duration_ms=intent_duration,
                        status_code="ERROR",
                        status_message=str(e),
                        attributes={
                            "document_type": "unknown",
                            "confidence": 0.0,
                            "error": str(e)
                        }
                    )
            except Exception as e:
                # Other errors in intent recognition - graceful degradation
                logger.error(f"Error in intent recognition for document {document_id}: {str(e)}", exc_info=True)
                document_type = "unknown"
                parse_result["intent_recognition"] = {
                    "document_type": "unknown",
                    "confidence": 0.0,
                    "reasoning": f"Intent recognition failed: {str(e)}"
                }
                
                # Update span with error
                if trace_id and observability_service and intent_span_id and intent_start is not None:
                    intent_duration = (time.time() - intent_start) * 1000
                    observability_service.update_span(
                        span_id=intent_span_id,
                        end_time=datetime.utcnow(),
                        duration_ms=intent_duration,
                        status_code="ERROR",
                        status_message=str(e),
                        attributes={
                            "document_type": "unknown",
                            "confidence": 0.0,
                            "error": str(e)
                        }
                    )
            
            # Step 3: Update database with results including document_type
            # Even if intent recognition failed, we mark parsing as successful
            document.parse_result = parse_result
            document.document_type = document_type
            document.parse_status = "success"  # Ensure status is success
            from datetime import datetime
            document.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Successfully parsed document with intent {document_id}: {document.name} (type: {document_type})")
            
            return {
                "success": True,
                "document_id": document_id,
                "parse_result": parse_result,
                "document_type": document_type
            }
            
        except Exception as e:
            logger.error(f"Error parsing document with intent {document_id}: {str(e)}", exc_info=True)
            
            # Update status to failed only if content parsing failed
            try:
                document = self.db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.parse_status = "failed"
                    from datetime import datetime
                    document.updated_at = datetime.utcnow()
                    self.db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update parse status: {str(update_error)}")
                self.db.rollback()
            
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e)
            }
    
    async def parse_document(self, document_id: int) -> Dict[str, Any]:
        """
        Parse document with intent recognition (backward compatibility)
        
        This method is kept for backward compatibility.
        It now calls parse_document_with_intent() to include intent recognition.
        
        Args:
            document_id: Document ID to parse
        
        Returns:
            Parsing result dictionary with intent recognition
        """
        return await self.parse_document_with_intent(document_id)
    
    async def parse_document_content_async(self, document_id: int) -> None:
        """
        Parse document content asynchronously (fire-and-forget)
        
        This method can be called without awaiting, useful for background tasks.
        Only parses content, does not perform intent recognition.
        
        Args:
            document_id: Document ID to parse
        """
        try:
            await self.parse_document_content(document_id)
        except Exception as e:
            logger.error(f"Error in async document content parsing: {str(e)}", exc_info=True)
    
    async def parse_document_with_intent_async(self, document_id: int) -> None:
        """
        Parse document with intent recognition asynchronously (fire-and-forget)
        
        This method can be called without awaiting, useful for background tasks.
        Performs both content parsing and intent recognition.
        
        Args:
            document_id: Document ID to parse
        """
        try:
            await self.parse_document_with_intent(document_id)
        except Exception as e:
            logger.error(f"Error in async document parsing with intent: {str(e)}", exc_info=True)
    
    async def parse_document_async(self, document_id: int) -> None:
        """
        Parse document asynchronously (fire-and-forget) - backward compatibility
        
        This method is kept for backward compatibility.
        It now calls parse_document_with_intent_async() to include intent recognition.
        
        Args:
            document_id: Document ID to parse
        """
        await self.parse_document_with_intent_async(document_id)


def parse_document_background(db: Session, document_id: int) -> None:
    """
    Background task function for parsing document with intent recognition
    Can be used with task queues like Celery or asyncio
    
    Args:
        db: Database session
        document_id: Document ID to parse
    """
    task = DocumentParsingTask(db)
    asyncio.run(task.parse_document_with_intent(document_id))
