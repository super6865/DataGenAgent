"""
Data Structure Understanding Agent for extracting field structures from API documents
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


class DataStructureAgent:
    """Agent for extracting data structure and field definitions from API documents"""
    
    def __init__(self, model_config_dict: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
        """
        Initialize data structure agent
        
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
            name="data_structure_extractor",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for data structure extraction"""
        return """你是一位专业的数据结构分析专家。你的任务是从接口文档中提取数据结构信息，包括字段定义、类型、约束条件等。

**重要：只提取请求参数（输入数据），不要提取响应数据（输出数据）**

提取要求：
1. **字段信息提取**（仅限请求参数和请求体）：
   - 字段名称
   - 字段类型（string, number, integer, boolean, object, array等）
   - 字段描述和业务含义
   - 是否必填（required）
   - 默认值（如果有）

2. **约束条件提取**：
   - 字符串长度限制（minLength, maxLength）
   - 数值范围（minimum, maximum）
   - 枚举值（enum）
   - 正则表达式（pattern）
   - 数组元素限制（minItems, maxItems）
   - 对象属性限制

3. **嵌套结构处理**：
   - 识别对象（object）类型的嵌套字段
   - 识别数组（array）类型及其元素结构
   - 处理多层嵌套结构

4. **输出格式**：
   必须严格按照以下JSON Schema格式返回结果：
   {
     "schema": {
       "type": "object",
       "properties": {
         "field_name": {
           "type": "string|number|integer|boolean|object|array",
           "description": "字段描述",
           "required": true/false,
           "default": "默认值（可选）",
           "constraints": {
             "minLength": 数字（可选）,
             "maxLength": 数字（可选）,
             "minimum": 数字（可选）,
             "maximum": 数字（可选）,
             "enum": ["值1", "值2"]（可选）,
             "pattern": "正则表达式"（可选）,
             "minItems": 数字（可选）,
             "maxItems": 数字（可选）
           }
         }
       },
       "required": ["必填字段1", "必填字段2"]
     },
     "fields": [
       {
         "name": "字段名",
         "type": "字段类型",
         "description": "字段描述",
         "required": true/false,
         "constraints": {...}
       }
     ],
     "examples": [
       {
         "description": "示例说明",
         "data": {...}
       }
     ]
   }

重要提示：
- **只提取请求参数和请求体的字段结构，不要提取响应数据的字段结构**
- **响应数据是输出，不是输入，不应包含在生成的数据结构中**
- **如果文档中包含"响应格式"、"响应示例"、"返回数据"等章节，应明确忽略这些内容**
- 必须返回有效的JSON格式
- schema必须符合JSON Schema规范
- 如果文档中没有明确说明，合理推断字段类型和约束
- 对于嵌套结构，要完整提取所有层级
- 如果无法确定某些信息，使用合理的默认值或标记为可选"""
    
    async def extract_data_structure(
        self,
        document_content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract data structure from API document content
        
        Args:
            document_content: Document content (can be raw text or structured content)
            document_metadata: Optional metadata about the document
        
        Returns:
            Dict with keys:
                - schema: JSON Schema object
                - fields: List of field definitions
                - examples: List of example data
        """
        try:
            # Prepare extraction prompt
            extraction_prompt = self._build_extraction_prompt(document_content, document_metadata)
            
            # Prepare messages for AutoGen
            messages = [
                {"role": "user", "content": extraction_prompt}
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
            result = self._parse_schema_response(response_text)
            
            logger.info(f"Data structure extracted: {len(result.get('fields', []))} fields")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting data structure: {str(e)}", exc_info=True)
            # Return default result on error
            return {
                "schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "fields": [],
                "examples": [],
                "error": str(e)
            }
    
    def _build_extraction_prompt(
        self,
        document_content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build extraction prompt for the agent"""
        prompt = "请从以下接口文档中提取数据结构信息，包括所有字段的定义、类型、约束条件等。\n\n"
        
        # Add metadata if available
        if document_metadata:
            if document_metadata.get("title"):
                prompt += f"文档标题: {document_metadata['title']}\n\n"
            if document_metadata.get("keywords"):
                keywords = ", ".join(document_metadata['keywords'][:10])
                prompt += f"关键词: {keywords}\n\n"
        
        # Add document content (limit length to avoid token limits)
        content_preview = document_content[:8000]  # Limit to 8000 characters for structure extraction
        if len(document_content) > 8000:
            content_preview += "\n\n[文档内容已截断，仅显示前8000字符]"
        
        prompt += f"接口文档内容:\n{content_preview}\n\n"
        prompt += "请按照要求提取数据结构信息，并返回JSON格式的结果。重点关注：\n"
        prompt += "1. 请求参数和请求体的字段结构（这是输入数据，必须提取）\n"
        prompt += "2. 字段的类型、约束条件、是否必填等信息\n"
        prompt += "3. 嵌套对象和数组的结构\n"
        prompt += "\n**重要：请忽略以下内容（这些是输出数据，不应提取）：**\n"
        prompt += "- 响应格式、响应示例、返回数据等章节\n"
        prompt += "- 响应体中的字段结构（如响应中的data、users等字段）\n"
        prompt += "- 任何标记为\"响应\"、\"输出\"、\"返回\"的内容\n"
        prompt += "\n只提取请求相关的数据结构，用于生成输入数据。\n"
        
        return prompt
    
    def _parse_schema_response(self, response_text: str) -> Dict[str, Any]:
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
                raise ValueError("Response is not a dictionary")
            
            # Ensure required keys exist
            if "schema" not in result:
                result["schema"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            
            if "fields" not in result:
                result["fields"] = []
            
            if "examples" not in result:
                result["examples"] = []
            
            # Validate schema structure
            schema = result.get("schema", {})
            if not isinstance(schema, dict):
                schema = {"type": "object", "properties": {}, "required": []}
                result["schema"] = schema
            
            # Ensure schema has required fields
            if "type" not in schema:
                schema["type"] = "object"
            if "properties" not in schema:
                schema["properties"] = {}
            if "required" not in schema:
                schema["required"] = []
            
            # Validate fields array
            if not isinstance(result["fields"], list):
                result["fields"] = []
            
            # Validate examples array
            if not isinstance(result["examples"], list):
                result["examples"] = []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {
                "schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "fields": [],
                "examples": [],
                "error": f"Failed to parse agent response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error validating schema response: {str(e)}")
            return {
                "schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "fields": [],
                "examples": [],
                "error": f"Error validating response: {str(e)}"
            }
