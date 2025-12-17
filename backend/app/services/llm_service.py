"""
LLM Service for data generation using AutoGen
"""
import asyncio
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from autogen import ConversableAgent
from app.utils.autogen_helper import create_autogen_config_from_model_config

logger = logging.getLogger(__name__)


class DataGenerationAgent:
    """AutoGen-based data generation agent using ConversableAgent"""
    
    def __init__(self, model_config_dict: Dict[str, Any]):
        """
        Initialize data generation agent
        
        Args:
            model_config_dict: Model configuration dictionary from database
        """
        self.model_config_dict = model_config_dict
        self.llm_config = create_autogen_config_from_model_config(model_config_dict)
        self.system_message = self._get_system_prompt()
        
        # Create AutoGen agent
        self.agent = ConversableAgent(
            name="data_generator",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for data generation"""
        return """You are a professional test data generation assistant. Your task is to generate test data based on user requirements.

Guidelines:
1. Generate data in the format requested by the user (JSON, CSV, Excel, or plain text)
2. If the user specifies a number of records, generate exactly that many records
3. Ensure data is realistic and diverse (avoid repetitive patterns)
4. For JSON format, return a valid JSON array or object
5. For CSV format, return comma-separated values with headers
6. For Excel format, return data in a structured format that can be converted to Excel
7. Include all fields requested by the user
8. Use appropriate data types (strings, numbers, dates, etc.)
9. If the user doesn't specify a format, default to JSON array format
10. Return only the data, without additional explanations or markdown formatting unless specifically requested

Example formats:
- JSON: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
- CSV: name,age\nJohn,30\nJane,25
- Text: Name: John, Age: 30\nName: Jane, Age: 25

Always generate data that matches the user's requirements exactly."""
    
    async def generate_data(
        self, 
        user_query: str,
        format_hint: Optional[str] = None,
        trace_id: Optional[str] = None,
        observability_service: Optional[Any] = None
    ) -> Tuple[str, Dict[str, int]]:
        """
        Generate test data based on user query
        
        Args:
            user_query: User's natural language query for data generation
            format_hint: Optional format hint (json, csv, excel, text)
            trace_id: Optional trace ID for observability
            observability_service: Optional observability service instance for logging
        
        Returns:
            Tuple of (generated_data: str, usage: Dict with input_tokens and output_tokens)
        """
        start_time = time.time()
        root_span_id = None
        
        try:
            # Span 1: Prepare request
            if trace_id and observability_service:
                prepare_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="prepare_request",
                    kind="internal",
                    attributes={
                        "user_query": user_query,
                        "format_hint": format_hint,
                        "model_type": self.model_config_dict.get('model_type'),
                        "model_version": self.model_config_dict.get('model_version'),
                    }
                )
                if prepare_span.get('success'):
                    root_span_id = prepare_span['data']['span_id']
                    prepare_start = time.time()
            
            # Enhance user query with format hint if provided
            enhanced_query = user_query
            if format_hint:
                enhanced_query = f"{user_query}\n\nPlease generate the data in {format_hint.upper()} format."
            
            # Prepare messages for AutoGen
            messages = [
                {"role": "user", "content": enhanced_query}
            ]
            
            # Span 2: Clear chat history
            if trace_id and observability_service and root_span_id:
                clear_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="clear_chat_history",
                    kind="internal",
                    parent_span_id=root_span_id,
                    attributes={"action": "clear_agent_chat_messages"}
                )
                clear_span_id = clear_span.get('data', {}).get('span_id') if clear_span.get('success') else None
                clear_start = time.time()
            
            # Clear agent chat history to ensure fresh conversation
            if hasattr(self.agent, 'chat_messages'):
                if isinstance(self.agent.chat_messages, list):
                    self.agent.chat_messages.clear()
                elif isinstance(self.agent.chat_messages, dict):
                    self.agent.chat_messages.clear()
            
            if trace_id and observability_service and root_span_id and 'clear_span_id' in locals():
                clear_duration = (time.time() - clear_start) * 1000
                observability_service.update_span(
                    span_id=clear_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=clear_duration,
                    status_code="OK"
                )
            
            # Span 3: Call LLM
            if trace_id and observability_service and root_span_id:
                llm_span = observability_service.create_span(
                    trace_id=trace_id,
                    name="call_llm",
                    kind="client",
                    parent_span_id=root_span_id,
                    attributes={
                        "input_messages": messages,  # 完整的输入消息
                        "model": f"{self.model_config_dict.get('model_type')}/{self.model_config_dict.get('model_version')}",
                        "llm_config": {  # 添加模型配置信息（排除敏感信息）
                            "model_type": self.model_config_dict.get('model_type'),
                            "model_version": self.model_config_dict.get('model_version'),
                            "temperature": self.model_config_dict.get('temperature'),
                            "max_tokens": self.model_config_dict.get('max_tokens'),
                        }
                    }
                )
                llm_span_id = llm_span.get('data', {}).get('span_id') if llm_span.get('success') else None
                llm_start = time.time()
            
            # Generate reply using AutoGen agent
            # Note: AutoGen's generate_reply is synchronous, but we're in async context
            # We need to run it in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.agent.generate_reply(messages=messages)
            )
            
            # Extract content from response
            if isinstance(response, dict):
                generated_data = response.get("content", "")
            elif hasattr(response, "content"):
                generated_data = response.content
            else:
                generated_data = str(response)
            
            # Extract token usage from agent's internal state
            input_tokens = 0
            output_tokens = 0
            try:
                if hasattr(self.agent, "client") and hasattr(self.agent.client, "cost"):
                    cost_info = self.agent.client.cost
                    if isinstance(cost_info, dict):
                        input_tokens = cost_info.get("prompt_tokens", 0) or cost_info.get("input_tokens", 0) or 0
                        output_tokens = cost_info.get("completion_tokens", 0) or cost_info.get("output_tokens", 0) or 0
            except Exception as e:
                logger.warning(f"Failed to extract token usage from AutoGen agent: {str(e)}")
            
            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
            
            # Update LLM span with response
            if trace_id and observability_service and root_span_id and 'llm_span_id' in locals():
                llm_duration = (time.time() - llm_start) * 1000
                observability_service.update_span(
                    span_id=llm_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=llm_duration,
                    status_code="OK",
                    attributes={  # 添加响应内容到 attributes
                        "output_content": generated_data,  # 完整的响应内容
                        "response_length": len(generated_data),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                    events=[{
                        "name": "llm_response",
                        "timestamp": datetime.utcnow().isoformat(),
                        "attributes": {
                            "response_length": len(generated_data),
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        }
                    }]
                )
            
            # Update root span
            if trace_id and observability_service and root_span_id:
                prepare_duration = (time.time() - prepare_start) * 1000
                observability_service.update_span(
                    span_id=root_span_id,
                    end_time=datetime.utcnow(),
                    duration_ms=prepare_duration,
                    status_code="OK",
                    events=[{
                        "name": "generation_complete",
                        "timestamp": datetime.utcnow().isoformat(),
                        "attributes": {
                            "usage": usage,
                            "data_length": len(generated_data)
                        }
                    }]
                )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Data generation completed in {execution_time_ms}ms, tokens: {usage}")
            
            return generated_data, usage
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Data generation failed after {execution_time_ms}ms: {str(e)}")
            
            # Update spans with error
            if trace_id and observability_service and root_span_id:
                try:
                    observability_service.update_span(
                        span_id=root_span_id,
                        end_time=datetime.utcnow(),
                        duration_ms=execution_time_ms,
                        status_code="ERROR",
                        status_message=str(e),
                        events=[{
                            "name": "error",
                            "timestamp": datetime.utcnow().isoformat(),
                            "attributes": {
                                "error": str(e)
                            }
                        }]
                    )
                except:
                    pass
            
            raise Exception(f"Failed to generate data: {str(e)}")
