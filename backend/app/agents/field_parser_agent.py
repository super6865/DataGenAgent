"""
Field Parser Agent for intelligently parsing JSON structures into field definitions
"""
import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from autogen import ConversableAgent
from app.utils.autogen_helper import create_autogen_config_from_model_config
from app.services.model_config_service import ModelConfigService

logger = logging.getLogger(__name__)


class FieldParserAgent:
    """Agent for intelligently parsing JSON structures into field definitions"""
    
    def __init__(self, model_config_dict: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
        """
        Initialize field parser agent
        
        Args:
            model_config_dict: Model configuration dictionary. If None, will fetch default from database
            db: Database session (required if model_config_dict is None)
        """
        if model_config_dict is None:
            if db is None:
                raise ValueError("Either model_config_dict or db session must be provided")
            # Get config for agent (default first, then first enabled)
            model_config_service = ModelConfigService(db)
            config_dict = model_config_service.get_config_for_agent(include_sensitive=False)
            if not config_dict:
                raise ValueError("No model configuration available. Please configure a model first.")
            # Get full config with decrypted API key for LLM
            config_id = config_dict.get('id')
            if config_id:
                model_config_dict = model_config_service.get_config_dict_for_llm(config_id)
            else:
                raise ValueError("Failed to get model configuration")
        
        self.model_config_dict = model_config_dict
        self.llm_config = create_autogen_config_from_model_config(model_config_dict)
        self.system_message = self._get_system_prompt()
        
        # Create AutoGen agent
        self.agent = ConversableAgent(
            name="field_parser",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for field parsing"""
        return """你是一位专业的数据结构分析专家。你的任务是从JSON示例中智能提取字段定义，包括字段类型、描述、约束条件等。

分析要求：
1. **字段类型推断**：
   - 准确识别基本类型（string, number, integer, boolean）
   - 识别日期时间格式（date, datetime）
   - 识别对象（object）和数组（array）类型
   - 对于null值，根据字段名和上下文推断最可能的类型

2. **字段描述生成**：
   - 根据字段名称推断业务含义
   - 结合字段值示例生成准确的描述
   - 对于嵌套结构，描述要清晰说明层级关系

3. **约束条件识别**：
   - 字符串长度限制（minLength, maxLength）
   - 数值范围（minimum, maximum）
   - 枚举值（enum）- 如果数组中有多个不同值，判断是否为枚举
   - 正则表达式模式（pattern）- 识别邮箱、URL、手机号等格式
   - 数组元素限制（minItems, maxItems）

4. **嵌套结构处理**：
   - 完整提取对象（object）类型的所有嵌套字段
   - 处理数组（array）中对象的字段结构
   - 支持多层嵌套，保持完整的层级关系
   - 为嵌套字段生成合理的路径和描述

5. **必填字段判断**：
   - 如果JSON示例中字段存在且非null，可能为必填
   - 根据字段名称（如id, name等）判断是否通常为必填

输出格式：
必须严格按照以下JSON格式返回结果：
{
  "schema": {
    "type": "object",
    "properties": {
      "field_name": {
        "type": "string|number|integer|boolean|object|array|date|datetime",
        "description": "字段的业务描述",
        "required": true/false,
        "constraints": {
          "minLength": 数字（可选）,
          "maxLength": 数字（可选）,
          "minimum": 数字（可选）,
          "maximum": 数字（可选）,
          "enum": ["值1", "值2"]（可选）,
          "pattern": "正则表达式"（可选）,
          "minItems": 数字（可选）,
          "maxItems": 数字（可选）
        },
        "properties": {...}（如果是object类型）,
        "items": {...}（如果是array类型）
      }
    },
    "required": ["必填字段1", "必填字段2"]
  },
  "field_definitions": [
    {
      "name": "字段名",
      "type": "字段类型",
      "description": "字段描述",
      "required": true/false,
      "constraints": {...},
      "properties": [...]（如果是object类型，包含嵌套字段）,
      "items": {...}（如果是array类型）
    }
  ]
}

重要提示：
- 必须返回有效的JSON格式
- schema必须符合JSON Schema规范
- field_definitions是扁平化的字段列表，但需要包含嵌套字段的完整信息
- 对于嵌套字段，使用path字段标识层级关系（如 "user.address.city"）
- 对于object类型的字段，必须在properties字段中包含所有嵌套字段的完整定义
- 对于array类型的字段，如果items是object，必须在items.properties中包含所有嵌套字段的完整定义
- 嵌套字段也需要包含完整的类型、描述、约束等信息
- 如果无法确定某些信息，使用合理的默认值
- 特别关注嵌套对象和数组的处理，确保结构完整，包括多层嵌套"""
    
    async def parse_json(
        self,
        json_string: str
    ) -> Dict[str, Any]:
        """
        Parse JSON string to schema and field definitions using AI
        
        Args:
            json_string: JSON string to parse
        
        Returns:
            Dict with keys:
                - schema: JSON Schema object
                - field_definitions: List of field definitions
        """
        try:
            # Validate JSON first
            try:
                json_data = json.loads(json_string)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {str(e)}")
            
            # Prepare parsing prompt
            parsing_prompt = self._build_parsing_prompt(json_data, json_string)
            
            # Prepare messages for AutoGen
            messages = [
                {"role": "user", "content": parsing_prompt}
            ]
            
            # Clear agent chat history
            if hasattr(self.agent, 'chat_messages'):
                if isinstance(self.agent.chat_messages, list):
                    self.agent.chat_messages.clear()
                elif isinstance(self.agent.chat_messages, dict):
                    self.agent.chat_messages.clear()
            
            # Generate reply using AutoGen agent
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.agent.generate_reply(messages=messages)
            )
            
            # Extract content from response
            if isinstance(response, dict):
                response_text = response.get("content", "")
            elif hasattr(response, "content"):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Parse JSON from response
            result = self._parse_response(response_text)
            
            # Validate and normalize result
            result = self._normalize_result(result, json_data)
            
            logger.info(f"JSON parsed with agent: {len(result.get('field_definitions', []))} fields")
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing JSON with agent: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse JSON with agent: {str(e)}")
    
    def _build_parsing_prompt(
        self,
        json_data: Any,
        json_string: str
    ) -> str:
        """Build parsing prompt for the agent"""
        prompt = "请分析以下JSON数据结构，智能提取所有字段的定义信息。\n\n"
        
        # Add formatted JSON
        try:
            formatted_json = json.dumps(json_data, ensure_ascii=False, indent=2)
            # Limit length to avoid token limits
            if len(formatted_json) > 10000:
                formatted_json = formatted_json[:10000] + "\n\n[JSON内容已截断，仅显示前10000字符]"
            prompt += f"JSON数据:\n```json\n{formatted_json}\n```\n\n"
        except:
            # Fallback to original string
            if len(json_string) > 10000:
                json_string = json_string[:10000] + "\n\n[JSON内容已截断]"
            prompt += f"JSON数据:\n```json\n{json_string}\n```\n\n"
        
        prompt += "请仔细分析这个JSON结构，重点关注：\n"
        prompt += "1. 识别所有字段及其类型（包括嵌套字段）\n"
        prompt += "2. 根据字段名和值推断业务含义，生成准确的描述\n"
        prompt += "3. 识别约束条件（长度、范围、枚举、格式等）\n"
        prompt += "4. 判断哪些字段可能是必填的\n"
        prompt += "5. 完整处理嵌套对象和数组结构\n"
        prompt += "6. 对于数组，分析元素类型和结构\n\n"
        prompt += "请返回符合要求的JSON格式结果。"
        
        return prompt
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response from agent"""
        # Try to extract JSON from response
        # The response might contain markdown code blocks or extra text
        
        # Remove markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text.strip()
        
        try:
            result = json.loads(json_str)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError("Response is not a JSON object")
            
            # Ensure required keys exist
            if "schema" not in result:
                result["schema"] = {"type": "object", "properties": {}, "required": []}
            if "field_definitions" not in result:
                result["field_definitions"] = []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from agent response: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Agent response is not valid JSON: {str(e)}")
    
    def _normalize_result(
        self,
        result: Dict[str, Any],
        original_json: Any
    ) -> Dict[str, Any]:
        """Normalize and validate the parsed result"""
        # Ensure field_definitions is a list
        if not isinstance(result.get("field_definitions"), list):
            result["field_definitions"] = []
        
        # Ensure schema is valid
        if not isinstance(result.get("schema"), dict):
            result["schema"] = {"type": "object", "properties": {}, "required": []}
        
        # Recursive function to normalize a field and its nested structures
        def normalize_field(field: Dict[str, Any], path: str = "") -> Dict[str, Any]:
            """Recursively normalize a field definition"""
            if not isinstance(field, dict):
                return {}
            
            # Ensure required fields
            field_name = field.get("name", "")
            current_path = f"{path}.{field_name}" if path else field_name
            
            normalized_field = {
                "name": field_name,
                "type": field.get("type", "string"),
                "description": field.get("description", ""),
                "required": field.get("required", False),
                "constraints": field.get("constraints", {}),
            }
            
            # Handle nested structures - recursively normalize
            if normalized_field["type"] == "object" and "properties" in field:
                nested_properties = field["properties"]
                if isinstance(nested_properties, list):
                    # Recursively normalize all nested properties
                    normalized_properties = []
                    for nested_field in nested_properties:
                        normalized_nested = normalize_field(nested_field, current_path)
                        if normalized_nested:
                            normalized_properties.append(normalized_nested)
                    normalized_field["properties"] = normalized_properties
                    logger.debug(f"Normalized object field '{field_name}' with {len(normalized_properties)} nested properties")
            
            if normalized_field["type"] == "array" and "items" in field:
                items = field["items"]
                if isinstance(items, dict):
                    normalized_items = {
                        "type": items.get("type", "string")
                    }
                    # Handle array items that are objects with nested properties
                    if items.get("type") == "object" and "properties" in items:
                        nested_properties = items["properties"]
                        if isinstance(nested_properties, list):
                            # Recursively normalize nested properties in array items
                            normalized_properties = []
                            for nested_field in nested_properties:
                                normalized_nested = normalize_field(nested_field, f"{current_path}[]")
                                if normalized_nested:
                                    normalized_properties.append(normalized_nested)
                            normalized_items["properties"] = normalized_properties
                            logger.debug(f"Normalized array field '{field_name}' with object items containing {len(normalized_properties)} properties")
                    normalized_field["items"] = normalized_items
            
            return normalized_field
        
        # Normalize all field definitions
        normalized_fields = []
        for field in result.get("field_definitions", []):
            normalized_field = normalize_field(field)
            if normalized_field and normalized_field.get("name"):
                normalized_fields.append(normalized_field)
        
        result["field_definitions"] = normalized_fields
        logger.info(f"Normalized {len(normalized_fields)} field definitions with nested structures")
        
        return result
