"""
Document models
"""
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, JSON, Text
from datetime import datetime
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Document name
    file_path = Column(String(500), nullable=False)  # File storage path
    file_type = Column(String(50), nullable=False)  # File type: md, docx, pdf, txt
    file_size = Column(BigInteger, nullable=False)  # File size in bytes
    upload_time = Column(DateTime, default=datetime.utcnow, index=True)  # Upload time (indexed for sorting)
    parse_status = Column(String(20), nullable=False, default="pending", index=True)  # pending, parsing, success, failed (indexed for filtering)
    parse_result = Column(JSON, nullable=True)  # Parsed document content (structured JSON)
    document_type = Column(String(20), nullable=True)  # api, requirement, unknown
    created_by = Column(Integer, nullable=True)  # User ID who created the document
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
