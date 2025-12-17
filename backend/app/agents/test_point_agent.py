"""
Test Point Processing Agent for extracting test points and business rules from requirement documents
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


class TestPointAgent:
    """Agent for extracting test points and business rules from requirement documents"""
    
    def __init__(self, model_config_dict: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
        """
        Initialize test point agent
        
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
            name="test_point_extractor",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for test point extraction"""
        return """你是一位专业的测试分析和业务规则提取专家。你的任务是从需求文档中提取测试点、业务规则、数据实体等信息。

提取要求：
1. **测试点提取**：
   - 测试场景描述
   - 测试用例列表
   - 每个测试用例的输入条件和预期结果
   - 边界条件和异常情况

2. **业务实体提取**：
   - 业务实体的名称和描述
   - 实体包含的字段
   - 字段的类型、描述、约束
   - 实体之间的关系（一对一、一对多、多对多等）

3. **业务规则提取**：
   - 数据验证规则
   - 业务逻辑规则
   - 约束条件
   - 计算规则
   - 状态转换规则

4. **输出格式**：
   必须严格按照以下JSON格式返回结果：
   {
     "test_points": [
       {
         "scenario": "测试场景描述",
         "description": "场景详细说明",
         "test_cases": [
           {
             "name": "测试用例名称",
             "description": "用例描述",
             "input_conditions": ["条件1", "条件2"],
             "expected_result": "预期结果",
             "test_data_requirements": {
               "required_fields": ["字段1", "字段2"],
               "field_constraints": {
                 "字段1": {
                   "type": "string",
                   "constraints": {...}
                 }
               }
             }
           }
         ],
         "business_rules": ["规则1", "规则2"]
       }
     ],
     "entities": [
       {
         "name": "实体名称",
         "description": "实体描述",
         "fields": [
           {
             "name": "字段名",
             "type": "字段类型",
             "description": "字段描述",
             "required": true/false,
             "constraints": {...}
           }
         ],
         "relationships": [
           {
             "target_entity": "关联实体名",
             "type": "one-to-one|one-to-many|many-to-many",
             "description": "关系描述"
           }
         ]
       }
     ],
     "business_rules": [
       {
         "rule_name": "规则名称",
         "description": "规则描述",
         "condition": "规则条件",
         "action": "规则动作",
         "applies_to": ["实体名或字段名"]
       }
     ]
   }

重要提示：
- 必须返回有效的JSON格式
- 如果文档中没有明确说明，合理推断业务实体和规则
- 对于测试点，要覆盖正常流程、异常流程、边界情况
- 对于业务规则，要提取所有约束条件和验证规则
- 如果无法确定某些信息，使用合理的默认值或标记为可选"""
    
    async def extract_test_points(
        self,
        document_content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract test points and business rules from requirement document content
        
        Args:
            document_content: Document content (can be raw text or structured content)
            document_metadata: Optional metadata about the document
        
        Returns:
            Dict with keys:
                - test_points: List of test scenarios and cases
                - entities: List of business entities
                - business_rules: List of business rules
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
            result = self._parse_test_points_response(response_text)
            
            test_points_count = len(result.get('test_points', []))
            entities_count = len(result.get('entities', []))
            rules_count = len(result.get('business_rules', []))
            logger.info(f"Test points extracted: {test_points_count} scenarios, {entities_count} entities, {rules_count} rules")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting test points: {str(e)}", exc_info=True)
            # Return default result on error
            return {
                "test_points": [],
                "entities": [],
                "business_rules": [],
                "error": str(e)
            }
    
    def _build_extraction_prompt(
        self,
        document_content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build extraction prompt for the agent"""
        prompt = "请从以下需求文档中提取测试点、业务实体和业务规则信息。\n\n"
        
        # Add metadata if available
        if document_metadata:
            if document_metadata.get("title"):
                prompt += f"文档标题: {document_metadata['title']}\n\n"
            if document_metadata.get("keywords"):
                keywords = ", ".join(document_metadata['keywords'][:10])
                prompt += f"关键词: {keywords}\n\n"
        
        # Add document content (limit length to avoid token limits)
        content_preview = document_content[:8000]  # Limit to 8000 characters
        if len(document_content) > 8000:
            content_preview += "\n\n[文档内容已截断，仅显示前8000字符]"
        
        prompt += f"需求文档内容:\n{content_preview}\n\n"
        prompt += "请按照要求提取以下信息：\n"
        prompt += "1. 测试场景和测试用例（包括正常流程、异常流程、边界情况）\n"
        prompt += "2. 业务实体及其字段定义（包括类型、约束、关系）\n"
        prompt += "3. 业务规则和约束条件（包括验证规则、计算规则、状态转换等）\n"
        prompt += "4. 测试数据需求（每个测试用例需要哪些字段和数据）\n"
        
        return prompt
    
    def _parse_test_points_response(self, response_text: str) -> Dict[str, Any]:
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
            if "test_points" not in result:
                result["test_points"] = []
            
            if "entities" not in result:
                result["entities"] = []
            
            if "business_rules" not in result:
                result["business_rules"] = []
            
            # Validate arrays
            if not isinstance(result["test_points"], list):
                result["test_points"] = []
            
            if not isinstance(result["entities"], list):
                result["entities"] = []
            
            if not isinstance(result["business_rules"], list):
                result["business_rules"] = []
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {
                "test_points": [],
                "entities": [],
                "business_rules": [],
                "error": f"Failed to parse agent response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error validating test points response: {str(e)}")
            return {
                "test_points": [],
                "entities": [],
                "business_rules": [],
                "error": f"Error validating response: {str(e)}"
            }
