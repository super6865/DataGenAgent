"""
API decorators for error handling
"""
from functools import wraps
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


def handle_api_errors(func):
    """Decorator to handle API errors"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    return wrapper


def handle_not_found(message: str = "Resource not found"):
    """Decorator factory for handling not found errors"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if result is None or (isinstance(result, dict) and result.get('data') is None):
                raise HTTPException(status_code=404, detail=message)
            return result
        return wrapper
    return decorator
