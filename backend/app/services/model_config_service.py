"""
Model configuration service
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.model_config import ModelConfig
from app.utils.crypto import encrypt_api_key, decrypt_api_key, mask_api_key
import logging

logger = logging.getLogger(__name__)


class ModelConfigService:
    """Service for managing model configurations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_configs(
        self, 
        include_sensitive: bool = False, 
        skip: int = 0, 
        limit: int = 100
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get all model configurations with pagination"""
        try:
            query = self.db.query(ModelConfig)
            total = query.count()
            configs = query.order_by(ModelConfig.id.asc()).offset(skip).limit(limit).all()
            
            result = []
            for config in configs:
                config_dict = self._config_to_dict(config, include_sensitive)
                result.append(config_dict)
            
            return result, total
        except Exception as e:
            logger.error(f"Error in get_all_configs: {str(e)}", exc_info=True)
            return [], 0
    
    def get_config_by_id(
        self, 
        config_id: int, 
        include_sensitive: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID"""
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            return None
        return self._config_to_dict(config, include_sensitive)
    
    def get_default_config(self, include_sensitive: bool = False) -> Optional[Dict[str, Any]]:
        """Get default model configuration"""
        config = self.db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_enabled == True
        ).first()
        if not config:
            return None
        return self._config_to_dict(config, include_sensitive)
    
    def get_config_for_agent(self, include_sensitive: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get model config for agent (default first, then first enabled)
        
        Priority:
        1. Default config (is_default=True and is_enabled=True)
        2. First enabled config (is_enabled=True, ordered by id)
        3. None if no config available
        
        Args:
            include_sensitive: Whether to include sensitive information
        
        Returns:
            Model configuration dictionary or None
        """
        # 1. Try to get default config
        default_config = self.get_default_config(include_sensitive)
        if default_config:
            return default_config
        
        # 2. Get first enabled config
        config = self.db.query(ModelConfig).filter(
            ModelConfig.is_enabled == True
        ).order_by(ModelConfig.id.asc()).first()
        if config:
            return self._config_to_dict(config, include_sensitive)
        
        return None
    
    def create_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new model configuration"""
        try:
            # Encrypt API key before storing
            encrypted_api_key = encrypt_api_key(config_data['api_key'])
            
            config = ModelConfig(
                config_name=config_data['config_name'],
                model_type=config_data['model_type'],
                model_version=config_data['model_version'],
                api_key=encrypted_api_key,
                api_base=config_data.get('api_base'),
                temperature=config_data.get('temperature'),
                max_tokens=config_data.get('max_tokens'),
                timeout=config_data.get('timeout', 120),
                is_enabled=config_data.get('is_enabled', True),
                is_default=config_data.get('is_default', False),
            )
            
            # If this is set as default, unset other defaults
            if config.is_default:
                self.db.query(ModelConfig).update({ModelConfig.is_default: False})
            
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            
            return {
                'success': True,
                'data': self._config_to_dict(config, include_sensitive=False),
                'message': 'Configuration created successfully'
            }
        except IntegrityError as e:
            self.db.rollback()
            return {
                'success': False,
                'message': f'Configuration name already exists: {str(e)}'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create config: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create configuration: {str(e)}'
            }
    
    def update_config(
        self, 
        config_id: int, 
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update model configuration"""
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            return {
                'success': False,
                'message': 'Configuration not found'
            }
        
        try:
            # Update fields
            if 'config_name' in config_data:
                config.config_name = config_data['config_name']
            if 'model_type' in config_data:
                config.model_type = config_data['model_type']
            if 'model_version' in config_data:
                config.model_version = config_data['model_version']
            if 'api_key' in config_data:
                config.api_key = encrypt_api_key(config_data['api_key'])
            if 'api_base' in config_data:
                config.api_base = config_data['api_base']
            if 'temperature' in config_data:
                config.temperature = config_data['temperature']
            if 'max_tokens' in config_data:
                config.max_tokens = config_data['max_tokens']
            if 'timeout' in config_data:
                config.timeout = config_data['timeout']
            if 'is_enabled' in config_data:
                config.is_enabled = config_data['is_enabled']
            if 'is_default' in config_data:
                config.is_default = config_data['is_default']
                # If setting as default, unset other defaults
                if config.is_default:
                    self.db.query(ModelConfig).filter(
                        ModelConfig.id != config_id
                    ).update({ModelConfig.is_default: False})
            
            self.db.commit()
            self.db.refresh(config)
            
            return {
                'success': True,
                'data': self._config_to_dict(config, include_sensitive=False),
                'message': 'Configuration updated successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update config: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update configuration: {str(e)}'
            }
    
    def delete_config(self, config_id: int) -> Dict[str, Any]:
        """Delete model configuration"""
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            return {
                'success': False,
                'message': 'Configuration not found'
            }
        
        try:
            self.db.delete(config)
            self.db.commit()
            return {
                'success': True,
                'message': 'Configuration deleted successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete config: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to delete configuration: {str(e)}'
            }
    
    def get_config_dict_for_llm(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get model config as dictionary for LLM service (with decrypted API key)"""
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            return None
        
        return {
            'model_type': config.model_type,
            'model_version': config.model_version,
            'api_key': decrypt_api_key(config.api_key),
            'api_base': config.api_base,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'timeout': config.timeout,
        }
    
    def _config_to_dict(
        self, 
        config: ModelConfig, 
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Convert ModelConfig to dictionary"""
        config_dict = {
            'id': config.id,
            'config_name': config.config_name,
            'model_type': config.model_type,
            'model_version': config.model_version,
            'api_base': config.api_base,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'timeout': config.timeout,
            'is_enabled': config.is_enabled,
            'is_default': config.is_default,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None,
        }
        
        if include_sensitive:
            config_dict['api_key'] = mask_api_key(config.api_key)
        
        return config_dict
