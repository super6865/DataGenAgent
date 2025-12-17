"""
AutoGen helper for data generation
"""
from typing import Dict, Any


def create_autogen_config_from_model_config(model_config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert model configuration dictionary to AutoGen configuration format
    
    Args:
        model_config_dict: Dictionary containing model configuration:
            - model_type: openai, qwen, deepseek, etc.
            - model_version: gpt-4, qwen-plus, etc.
            - api_key: API key for the model
            - api_base: Optional API base URL
            - temperature: Optional temperature parameter
            - max_tokens: Optional max tokens parameter
            - timeout: Request timeout in seconds
    
    Returns:
        AutoGen-compatible LLM configuration dictionary
    """
    model_type = model_config_dict.get('model_type', 'openai').lower()
    
    autogen_config = {
        "model": model_config_dict.get('model_version', 'gpt-4'),
        "api_key": model_config_dict.get('api_key'),
    }
    
    if model_config_dict.get('api_base'):
        autogen_config["base_url"] = model_config_dict['api_base']
    
    # Handle temperature parameter
    temperature = model_config_dict.get('temperature')
    if temperature is not None:
        if isinstance(temperature, str):
            try:
                temperature = float(temperature)
            except (ValueError, TypeError):
                temperature = None
        elif not isinstance(temperature, (int, float)):
            try:
                temperature = float(temperature)
            except (ValueError, TypeError):
                temperature = None
        if temperature is not None:
            autogen_config["temperature"] = temperature
    
    # Handle max_tokens parameter
    max_tokens = model_config_dict.get('max_tokens')
    if max_tokens is not None:
        if isinstance(max_tokens, str):
            try:
                max_tokens = int(max_tokens)
            except (ValueError, TypeError):
                max_tokens = None
        elif not isinstance(max_tokens, int):
            try:
                max_tokens = int(max_tokens)
            except (ValueError, TypeError):
                max_tokens = None
        if max_tokens is not None:
            autogen_config["max_tokens"] = max_tokens
    
    # Set default base_url based on model_type
    if model_type in ['qwen', 'aliyun', 'dashscope']:
        if not autogen_config.get('base_url'):
            autogen_config["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    elif model_type == 'deepseek':
        if not autogen_config.get('base_url'):
            autogen_config["base_url"] = "https://api.deepseek.com"
    elif model_type == 'openai':
        if not autogen_config.get('base_url'):
            autogen_config["base_url"] = "https://api.openai.com/v1"
    
    # Handle timeout
    timeout = model_config_dict.get('timeout', 120)
    if isinstance(timeout, str):
        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            timeout = 120
    elif not isinstance(timeout, int):
        timeout = int(timeout) if timeout is not None else 120
    
    autogen_config["timeout"] = timeout
    
    # Build LLM config for AutoGen
    llm_config = {
        "config_list": [autogen_config],
        "timeout": timeout,
        "cache_seed": None,  # 禁用缓存，确保每次调用都真正请求 LLM API
    }
    
    if model_config_dict.get('temperature') is not None:
        llm_config["temperature"] = model_config_dict['temperature']
    
    return llm_config
