"""
Intent Recognition Agent for classifying document types
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


class IntentRecognitionAgent:
    """Agent for recognizing document type (API document vs Requirement document)"""
    
    def __init__(self, model_config_dict: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
        """
        Initialize intent recognition agent
        
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
            name="intent_recognizer",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for intent recognition"""
        return """你是一位专业的文档分析专家。你的任务是分析文档内容，判断文档类型。

文档类型定义：
1. **接口文档 (api)**: 包含以下特征的内容
   - API接口定义、端点说明
   - 请求参数、请求体结构
   - 响应格式、响应字段说明
   - HTTP方法（GET、POST、PUT、DELETE等）
   - 状态码说明
   - 字段类型、约束条件
   - 示例请求和响应

2. **需求文档 (requirement)**: 包含以下特征的内容
   - 业务需求描述
   - 功能需求说明
   - 测试场景和测试点
   - 业务规则和约束
   - 用户故事、用例描述
   - 业务流程说明
   - 数据实体和关系

分析要求：
1. 仔细阅读文档内容
2. 识别文档的主要特征和关键词
3. 判断文档更符合哪种类型
4. 给出置信度评分（0.0-1.0）
5. 提供识别理由

输出格式：
请严格按照以下JSON格式返回结果，不要包含任何其他文字：
{
  "document_type": "api" 或 "requirement",
  "confidence": 0.0-1.0之间的数字,
  "reasoning": "详细的识别理由，说明为什么判断为该类型"
}

重要提示：
- 必须返回有效的JSON格式
- document_type只能是"api"或"requirement"
- confidence必须是0.0到1.0之间的浮点数
- 如果文档同时包含两种类型的特征，选择更主要或更明显的类型"""
    
    async def recognize_document_type(
        self,
        document_content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Recognize document type from content
        
        Args:
            document_content: Document content (can be raw text or structured content)
            document_metadata: Optional metadata about the document
        
        Returns:
            Dict with keys:
                - document_type: "api" | "requirement"
                - confidence: float (0.0-1.0)
                - reasoning: str
        """
        try:
            # Prepare analysis prompt
            analysis_prompt = self._build_analysis_prompt(document_content, document_metadata)
            
            # Prepare messages for AutoGen
            messages = [
                {"role": "user", "content": analysis_prompt}
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
            
            logger.info(f"Document type recognized: {result['document_type']} (confidence: {result['confidence']})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error recognizing document type: {str(e)}", exc_info=True)
            # Return default result on error
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "reasoning": f"Error during recognition: {str(e)}"
            }
    
    def _build_analysis_prompt(
        self,
        document_content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build analysis prompt for the agent"""
        prompt = "请分析以下文档内容，判断它是接口文档还是需求文档。\n\n"
        
        # Add metadata if available
        if document_metadata:
            if document_metadata.get("title"):
                prompt += f"文档标题: {document_metadata['title']}\n\n"
            if document_metadata.get("keywords"):
                keywords = ", ".join(document_metadata['keywords'][:10])
                prompt += f"关键词: {keywords}\n\n"
        
        # Add document content (limit length to avoid token limits)
        content_preview = document_content[:5000]  # Limit to 5000 characters
        if len(document_content) > 5000:
            content_preview += "\n\n[文档内容已截断，仅显示前5000字符]"
        
        prompt += f"文档内容:\n{content_preview}\n\n"
        prompt += "请按照要求返回JSON格式的分析结果。"
        
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
                raise ValueError("Response is not a dictionary")
            
            # Validate document_type
            document_type = result.get("document_type", "").lower()
            if document_type not in ["api", "requirement"]:
                logger.warning(f"Invalid document_type: {document_type}, defaulting to 'unknown'")
                document_type = "unknown"
            
            # Validate confidence
            confidence = result.get("confidence", 0.0)
            try:
                confidence = float(confidence)
                if confidence < 0.0:
                    confidence = 0.0
                elif confidence > 1.0:
                    confidence = 1.0
            except (ValueError, TypeError):
                confidence = 0.0
            
            # Get reasoning
            reasoning = result.get("reasoning", "No reasoning provided")
            if not isinstance(reasoning, str):
                reasoning = str(reasoning)
            
            return {
                "document_type": document_type,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"Response text: {response_text}")
            return {
                "document_type": "unknown",
                "confidence": 0.0,
                "reasoning": f"Failed to parse agent response: {str(e)}"
            }
