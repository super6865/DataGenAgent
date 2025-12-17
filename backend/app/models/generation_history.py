"""
Generation history models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from app.core.database import Base


class GenerationHistory(Base):
    __tablename__ = "generation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(Text, nullable=False)  # User's query/request
    generated_data = Column(Text, nullable=False)  # Generated data (stored as JSON string)
    data_format = Column(String(20), nullable=False)  # json, csv, excel, text
    model_used = Column(String(100), nullable=True)  # Model name used for generation
    model_config_id = Column(Integer, nullable=True)  # Reference to model_config
    input_type = Column(String(20), nullable=True, default="text")  # text, document, datasource, mixed
    references = Column(JSON, nullable=True)  # List of referenced resources
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
