"""
Observability service for trace and span management
"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.orm.attributes import flag_modified
from app.models.observability import Trace, Span
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ObservabilityService:
    """Service for managing traces and spans"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_trace(
        self,
        service_name: str,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new trace"""
        try:
            trace_id = str(uuid.uuid4())
            logger.info(f"Creating trace with trace_id: {trace_id}")
            trace = Trace(
                trace_id=trace_id,
                service_name=service_name,
                operation_name=operation_name,
                start_time=datetime.utcnow(),
                attributes=attributes or {}
            )
            
            self.db.add(trace)
            self.db.commit()
            self.db.refresh(trace)
            
            # 验证 trace 是否真的创建成功
            verify_trace = self.db.query(Trace).filter(Trace.trace_id == trace_id).first()
            if not verify_trace:
                logger.error(f"Trace created but not found after commit: {trace_id}")
                return {
                    'success': False,
                    'message': f'Trace created but not found in database: {trace_id}'
                }
            
            logger.info(f"Trace created and verified successfully: {trace_id}")
            return {
                'success': True,
                'data': self._trace_to_dict(trace),
                'message': 'Trace created successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create trace: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Failed to create trace: {str(e)}'
            }
    
    def update_trace(
        self,
        trace_id: str,
        end_time: Optional[datetime] = None,
        duration_ms: Optional[float] = None,
        status_code: Optional[str] = None,
        status_message: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update trace with end time and status"""
        try:
            trace = self.db.query(Trace).filter(Trace.trace_id == trace_id).first()
            if not trace:
                return {
                    'success': False,
                    'message': 'Trace not found'
                }
            
            if end_time:
                trace.end_time = end_time
            if duration_ms is not None:
                trace.duration_ms = duration_ms
            if status_code:
                trace.status_code = status_code
            if status_message:
                trace.status_message = status_message
            if attributes:
                if trace.attributes:
                    # Merge attributes
                    merged_attributes = {**(trace.attributes or {}), **attributes}
                    trace.attributes = merged_attributes
                else:
                    trace.attributes = attributes
                # 标记 attributes 字段已修改，确保 SQLAlchemy 检测到变更
                flag_modified(trace, 'attributes')
            
            self.db.commit()
            self.db.refresh(trace)
            
            return {
                'success': True,
                'data': self._trace_to_dict(trace),
                'message': 'Trace updated successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update trace: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update trace: {str(e)}'
            }
    
    def create_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: Optional[str] = None,
        kind: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Create a new span"""
        try:
            span_id = str(uuid.uuid4())
            span = Span(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                name=name,
                kind=kind,
                start_time=datetime.utcnow(),
                attributes=attributes or {},
                events=events or []
            )
            
            self.db.add(span)
            self.db.commit()
            self.db.refresh(span)
            
            return {
                'success': True,
                'data': self._span_to_dict(span),
                'message': 'Span created successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create span: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create span: {str(e)}'
            }
    
    def update_span(
        self,
        span_id: str,
        end_time: Optional[datetime] = None,
        duration_ms: Optional[float] = None,
        status_code: Optional[str] = None,
        status_message: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Update span with end time and status"""
        try:
            span = self.db.query(Span).filter(Span.span_id == span_id).first()
            if not span:
                return {
                    'success': False,
                    'message': 'Span not found'
                }
            
            if end_time:
                span.end_time = end_time
            if duration_ms is not None:
                span.duration_ms = duration_ms
            if status_code:
                span.status_code = status_code
            if status_message:
                span.status_message = status_message
            if attributes:
                if span.attributes:
                    span.attributes.update(attributes)
                else:
                    span.attributes = attributes
                # 标记 attributes 字段已修改，确保 SQLAlchemy 检测到变更
                flag_modified(span, 'attributes')
            if events is not None:
                if span.events:
                    span.events.extend(events)
                else:
                    span.events = events
                # 标记 events 字段已修改
                flag_modified(span, 'events')
            
            self.db.commit()
            self.db.refresh(span)
            
            return {
                'success': True,
                'data': self._span_to_dict(span),
                'message': 'Span updated successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update span: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update span: {str(e)}'
            }
    
    def get_trace_list(
        self,
        skip: int = 0,
        limit: int = 100,
        service_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get list of traces with pagination and filters"""
        try:
            query = self.db.query(Trace)
            
            if service_name:
                query = query.filter(Trace.service_name == service_name)
            if start_time:
                query = query.filter(Trace.start_time >= start_time)
            if end_time:
                query = query.filter(Trace.start_time <= end_time)
            
            total = query.count()
            traces = query.order_by(Trace.start_time.desc()).offset(skip).limit(limit).all()
            
            result = [self._trace_to_dict(t) for t in traces] if traces else []
            return result, total
        except Exception as e:
            logger.error(f"Error in get_trace_list: {str(e)}", exc_info=True)
            return [], 0
    
    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace by trace_id"""
        trace = self.db.query(Trace).filter(Trace.trace_id == trace_id).first()
        if not trace:
            return None
        return self._trace_to_dict(trace)
    
    def get_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace with all spans"""
        # 去除首尾空格
        original_trace_id = trace_id
        trace_id = trace_id.strip() if trace_id else trace_id
        logger.info(f"Querying trace with trace_id: {trace_id} (length: {len(trace_id)}, original: '{original_trace_id}')")
        
        trace = self.db.query(Trace).filter(Trace.trace_id == trace_id).first()
        if not trace:
            # 调试：查询所有 trace_id，用于排查
            all_traces = self.db.query(Trace.trace_id).all()
            all_trace_ids = [t[0] for t in all_traces]
            logger.warning(
                f"Trace not found. "
                f"Requested trace_id: '{trace_id}' (length: {len(trace_id)}), "
                f"Total traces in DB: {len(all_trace_ids)}, "
                f"Sample trace_ids: {all_trace_ids[:5]}"
            )
            return None
        
        spans = self.db.query(Span).filter(Span.trace_id == trace_id).all()
        logger.info(f"Found trace with {len(spans)} spans")
        
        return {
            'trace': self._trace_to_dict(trace),
            'spans': [self._span_to_dict(s) for s in spans]
        }
    
    def get_spans_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a trace"""
        spans = self.db.query(Span).filter(Span.trace_id == trace_id).all()
        return [self._span_to_dict(s) for s in spans]
    
    def _trace_to_dict(self, trace: Trace) -> Dict[str, Any]:
        """Convert Trace to dictionary"""
        return {
            'trace_id': trace.trace_id,
            'service_name': trace.service_name,
            'operation_name': trace.operation_name,
            'start_time': trace.start_time.isoformat() if trace.start_time else None,
            'end_time': trace.end_time.isoformat() if trace.end_time else None,
            'duration_ms': trace.duration_ms,
            'status_code': trace.status_code,
            'status_message': trace.status_message,
            'attributes': trace.attributes or {},
        }
    
    def _span_to_dict(self, span: Span) -> Dict[str, Any]:
        """Convert Span to dictionary"""
        return {
            'span_id': span.span_id,
            'trace_id': span.trace_id,
            'parent_span_id': span.parent_span_id,
            'name': span.name,
            'kind': span.kind,
            'start_time': span.start_time.isoformat() if span.start_time else None,
            'end_time': span.end_time.isoformat() if span.end_time else None,
            'duration_ms': span.duration_ms,
            'status_code': span.status_code,
            'status_message': span.status_message,
            'attributes': span.attributes or {},
            'events': span.events or [],
            'links': span.links or [],
        }
