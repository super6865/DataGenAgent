"""
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import data_generation, model_config, history, observability, documents, resource_library, data_templates

app = FastAPI(
    title="DataGenAgent API",
    description="DataGenAgent - AI-powered test data generation tool with AutoGen",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_generation.router, prefix="/api/v1/data-generation", tags=["data-generation"])
app.include_router(model_config.router, prefix="/api/v1/model-config", tags=["model-config"])
app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
app.include_router(observability.router, prefix="/api/v1/observability", tags=["observability"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(resource_library.router, prefix="/api/v1/resource-library", tags=["resource-library"])
app.include_router(data_templates.router, prefix="/api/v1/data-templates", tags=["data-templates"])


@app.get("/")
async def root():
    return {"message": "DataGenAgent API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
