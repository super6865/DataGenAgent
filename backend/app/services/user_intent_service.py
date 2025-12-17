"""
User Intent Recognition Service for classifying user queries
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


class UserIntentService:
    """Service for recognizing user query intent (data-related vs chat)"""
    
    def __init__(self, model_config_dict: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
        """
        Initialize user intent recognition service
        
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
            name="user_intent_recognizer",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for user intent recognition"""
        return """你是一位专业的用户意图识别专家。你的任务是分析用户的查询，判断用户的意图类型。

意图类型定义：
1. **数据相关 (data_related)**: 与数据生成、数据分析、测试数据相关的查询
   - 数据生成：生成测试数据、创建数据、构造数据等
   - 数据分析：分析数据、统计信息、数据验证等
   - 测试数据：测试用例数据、模拟数据、样本数据等
   - 数据格式：JSON、CSV、Excel等数据格式相关
   - 数据结构：字段定义、数据模型、数据规范等
   - 数据验证：数据校验、数据质量检查等

2. **闲聊类 (chat)**: 与数据生成和数据分析无关的查询
   - 天气查询：今天天气怎么样、天气预报等
   - 自我介绍：你是谁、介绍一下自己等
   - 日常聊天：你好、在吗、闲聊等
   - 无关咨询：其他与数据生成和数据分析无关的问题
   - 通用问答：与业务无关的通用问题

分析要求：
1. 仔细分析用户查询的内容和意图
2. 识别查询中的关键词和语义
3. 判断查询更符合哪种类型
4. 给出置信度评分（0.0-1.0）
5. 提供识别理由

输出格式：
请严格按照以下JSON格式返回结果，不要包含任何其他文字：
{
  "intent_type": "data_related" 或 "chat",
  "confidence": 0.0-1.0之间的数字,
  "reasoning": "详细的识别理由，说明为什么判断为该类型"
}

重要提示：
- 必须返回有效的JSON格式
- intent_type只能是"data_related"或"chat"
- confidence必须是0.0到1.0之间的浮点数
- 如果查询与数据生成或数据分析相关，即使包含其他内容，也应判断为"data_related"
- 只有明确与数据生成和数据分析无关的查询才判断为"chat"
"""
    
    async def recognize_intent(
        self,
        user_query: str
    ) -> Dict[str, Any]:
        """
        Recognize user query intent
        
        Args:
            user_query: User's query text
        
        Returns:
            Dict with keys:
                - intent_type: "data_related" | "chat"
                - confidence: float (0.0-1.0)
                - reasoning: str
        """
        try:
            # Prepare analysis prompt
            analysis_prompt = self._build_analysis_prompt(user_query)
            
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
            
            logger.info(f"User intent recognized: {result['intent_type']} (confidence: {result['confidence']})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error recognizing user intent: {str(e)}", exc_info=True)
            # Return default result on error (data_related to allow processing)
            return {
                "intent_type": "data_related",
                "confidence": 0.0,
                "reasoning": f"Error during recognition: {str(e)}. Defaulting to data_related to avoid blocking valid requests."
            }
    
    def _build_analysis_prompt(self, user_query: str) -> str:
        """Build analysis prompt for the agent"""
        prompt = "请分析以下用户查询，判断它是数据生成/数据分析相关的问题，还是闲聊类问题。\n\n"
        prompt += f"用户查询:\n{user_query}\n\n"
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
            
            # Validate intent_type
            intent_type = result.get("intent_type", "").lower()
            if intent_type not in ["data_related", "chat"]:
                logger.warning(f"Invalid intent_type: {intent_type}, defaulting to 'data_related'")
                intent_type = "data_related"  # Default to data_related to avoid blocking
            
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
                "intent_type": intent_type,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"Response text: {response_text}")
            # Default to data_related to avoid blocking valid requests
            return {
                "intent_type": "data_related",
                "confidence": 0.0,
                "reasoning": f"Failed to parse agent response: {str(e)}. Defaulting to data_related to avoid blocking."
            }

