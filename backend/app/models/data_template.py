"""
Data template models
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Index
from datetime import datetime
from app.core.database import Base


class DataTemplate(Base):
    __tablename__ = "data_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)  # Template name
    description = Column(Text, nullable=True)  # Template description
    schema = Column(JSON, nullable=False)  # JSON Schema structure
    field_definitions = Column(JSON, nullable=False)  # Field definitions list
    example_data = Column(JSON, nullable=True)  # Example data (optional)
    created_by = Column(Integer, nullable=True, index=True)  # User ID who created the template
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # Creation time
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Update time
