"""
Model configuration models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from datetime import datetime
from app.core.database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(255), nullable=False, unique=True, index=True)
    model_type = Column(String(50), nullable=False)  # openai, aliyun, deepseek, qwen, etc.
    model_version = Column(String(100), nullable=False)  # gpt-4, qwen-plus, etc.
    api_key = Column(Text, nullable=False)  # Encrypted storage recommended
    api_base = Column(String(500), nullable=True)  # API base URL
    temperature = Column(Float, nullable=True)  # Optional temperature parameter
    max_tokens = Column(Integer, nullable=True)  # Optional max tokens
    timeout = Column(Integer, default=120, nullable=False)  # Request timeout in seconds (default 120)
    is_enabled = Column(Boolean, default=True, nullable=False)  # Enable/disable flag
    is_default = Column(Boolean, default=False, nullable=False)  # Default model flag
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
