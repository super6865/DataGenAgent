"""
Generation history service
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.generation_history import GenerationHistory
import logging

logger = logging.getLogger(__name__)


class GenerationHistoryService:
    """Service for managing generation history"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_history(
        self,
        user_query: str,
        generated_data: str,
        data_format: str,
        model_used: Optional[str] = None,
        model_config_id: Optional[int] = None,
        input_type: Optional[str] = None,
        references: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create a new generation history record"""
        try:
            history = GenerationHistory(
                user_query=user_query,
                generated_data=generated_data,
                data_format=data_format,
                model_used=model_used,
                model_config_id=model_config_id,
                input_type=input_type or "text",
                references=references,
            )
            
            self.db.add(history)
            self.db.commit()
            self.db.refresh(history)
            
            return {
                'success': True,
                'data': self._history_to_dict(history),
                'message': 'History created successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create history: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create history: {str(e)}'
            }
    
    def get_history_list(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get list of generation history with pagination"""
        try:
            query = self.db.query(GenerationHistory)
            total = query.count()
            histories = query.order_by(
                GenerationHistory.created_at.desc()
            ).offset(skip).limit(limit).all()
            
            result = [self._history_to_dict(h) for h in histories] if histories else []
            return result, total
        except Exception as e:
            logger.error(f"Error in get_history_list: {str(e)}", exc_info=True)
            return [], 0
    
    def get_history_by_id(self, history_id: int) -> Optional[Dict[str, Any]]:
        """Get generation history by ID"""
        history = self.db.query(GenerationHistory).filter(
            GenerationHistory.id == history_id
        ).first()
        if not history:
            return None
        return self._history_to_dict(history)
    
    def delete_history(self, history_id: int) -> Dict[str, Any]:
        """Delete generation history"""
        history = self.db.query(GenerationHistory).filter(
            GenerationHistory.id == history_id
        ).first()
        if not history:
            return {
                'success': False,
                'message': 'History not found'
            }
        
        try:
            self.db.delete(history)
            self.db.commit()
            return {
                'success': True,
                'message': 'History deleted successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete history: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to delete history: {str(e)}'
            }
    
    def _history_to_dict(self, history: GenerationHistory) -> Dict[str, Any]:
        """Convert GenerationHistory to dictionary"""
        return {
            'id': history.id,
            'user_query': history.user_query,
            'generated_data': history.generated_data,
            'data_format': history.data_format,
            'model_used': history.model_used,
            'model_config_id': history.model_config_id,
            'input_type': history.input_type,
            'references': history.references,
            'created_at': history.created_at.isoformat() if history.created_at else None,
            'updated_at': history.updated_at.isoformat() if history.updated_at else None,
        }
