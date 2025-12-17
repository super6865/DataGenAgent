"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "DataGenAgent"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost:3306/datagenagent"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5174"]
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # LLM Configuration (Optional, can be configured via API)
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gpt-4"
    
    # Document Upload Configuration
    DOCUMENT_UPLOAD_DIR: str = "uploads/documents"
    MAX_DOCUMENT_SIZE: int = 50 * 1024 * 1024  # 50MB in bytes
    ALLOWED_DOCUMENT_TYPES: list = [".md", ".docx", ".pdf", ".txt"]
    
    # MCP Configuration
    MCP_SERVER_ENABLED: bool = False  # Enable MCP server integration
    MCP_SERVER_URL: str = ""  # MCP server URL (if using HTTP transport)
    MCP_SERVER_COMMAND: str = ""  # MCP server command (if using stdio transport)
    MCP_TIMEOUT: int = 300  # MCP request timeout in seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
