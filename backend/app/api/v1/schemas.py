"""
API schemas for data generation
"""
from pydantic import BaseModel
from typing import Optional, List


class DocumentReference(BaseModel):
    """Document reference schema"""
    type: str  # document, template, datasource, custom
    id: int
    name: str


class DataGenerationRequest(BaseModel):
    """Data generation request schema"""
    user_query: str
    model_config_id: Optional[int] = None
    format: Optional[str] = None  # json, csv, excel, text
    references: Optional[List[DocumentReference]] = None
