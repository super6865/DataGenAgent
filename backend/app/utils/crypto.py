"""
Cryptography utilities for API key encryption
"""
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Cache the Fernet instance
_fernet_instance = None


def get_fernet() -> Fernet:
    """
    Get or create a Fernet instance for encryption/decryption.
    Uses SECRET_KEY to derive a stable encryption key.
    
    Returns:
        Fernet instance
    """
    global _fernet_instance
    
    if _fernet_instance is None:
        # Derive a 32-byte key from SECRET_KEY using PBKDF2
        secret_key = settings.SECRET_KEY.encode('utf-8')
        salt = b'datagenagent_salt'  # Fixed salt for consistency
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(secret_key))
        _fernet_instance = Fernet(key)
    
    return _fernet_instance


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key (base64 encoded)
    """
    if not api_key:
        return api_key
    
    try:
        fernet = get_fernet()
        encrypted = fernet.encrypt(api_key.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {str(e)}")
        raise


def decrypt_api_key(encrypted: str) -> str:
    """
    Decrypt an API key from storage.
    
    Args:
        encrypted: Encrypted API key (base64 encoded)
        
    Returns:
        Plain text API key
    """
    if not encrypted:
        return encrypted
    
    # Check if already decrypted (for backward compatibility during migration)
    # If it doesn't look like a Fernet token, assume it's plain text
    if not encrypted.startswith('gAAAAAB'):
        # Might be plain text or old format, return as is
        return encrypted
    
    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to decrypt API key (might be plain text): {str(e)}")
        # If decryption fails, assume it's plain text (for backward compatibility)
        return encrypted


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display purposes.
    Shows first 4 characters and last 4 characters, masks the rest.
    
    Args:
        api_key: API key to mask (can be encrypted or plain text)
        
    Returns:
        Masked API key string (e.g., "sk-****abcd")
    """
    if not api_key:
        return ""
    
    # If it's encrypted, we can't mask it meaningfully, so show a generic mask
    if api_key.startswith('gAAAAAB'):
        return "****"
    
    # For plain text keys, show first 4 and last 4 characters
    if len(api_key) <= 8:
        return "****"
    
    return f"{api_key[:4]}****{api_key[-4:]}"
