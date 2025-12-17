"""
Observability models for trace and span tracking
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index
from datetime import datetime
from app.core.database import Base


class Trace(Base):
    __tablename__ = "traces"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(255), unique=True, nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    operation_name = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    status_code = Column(String(50), nullable=True)
    status_message = Column(Text, nullable=True)
    attributes = Column(JSON, nullable=True)  # Store trace-level attributes as JSON
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_trace_service_time', 'service_name', 'start_time'),
    )


class Span(Base):
    __tablename__ = "spans"

    id = Column(Integer, primary_key=True, index=True)
    span_id = Column(String(255), unique=True, nullable=False, index=True)
    trace_id = Column(String(255), nullable=False, index=True)
    parent_span_id = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(50), nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    status_code = Column(String(50), nullable=True)
    status_message = Column(Text, nullable=True)
    attributes = Column(JSON, nullable=True)  # Store input parameters as JSON
    events = Column(JSON, nullable=True)  # Store output/events as JSON array
    links = Column(JSON, nullable=True)  # Store links as JSON array
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_span_trace_time', 'trace_id', 'start_time'),
    )
