"""
Data parser service for parsing generated data
"""
import json
import re
import logging
from typing import Any, Optional, List, Dict

logger = logging.getLogger(__name__)


class DataParser:
    """Parser for generated data from LLM"""
    
    @staticmethod
    def parse_generated_data(content: str, format: Optional[str] = None) -> Any:
        """
        Parse generated data from LLM response
        
        Args:
            content: Raw content from LLM
            format: Expected format (json, csv, excel, text). If None, auto-detect
        
        Returns:
            Parsed data (dict, list, or string depending on format)
        """
        if not content:
            raise ValueError("Content is empty")
        
        # Auto-detect format if not specified
        if format is None:
            format = DataParser.detect_format(content)
        
        # Clean content (remove markdown code blocks if present)
        cleaned_content = DataParser._extract_from_markdown(content)
        
        if format == "json":
            return DataParser._parse_json(cleaned_content)
        elif format == "csv":
            return cleaned_content  # CSV is already text format
        elif format == "excel":
            return DataParser._parse_for_excel(cleaned_content)
        else:  # text
            return cleaned_content
    
    @staticmethod
    def _extract_from_markdown(content: str) -> str:
        """Extract content from markdown code blocks"""
        # Try to find JSON code block
        json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```'
        json_match = re.search(json_pattern, content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find any code block
        code_pattern = r'```[a-z]*\s*([\s\S]*?)\s*```'
        code_match = re.search(code_pattern, content, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # If no code block found, return original content
        return content.strip()
    
    @staticmethod
    def _parse_json(content: str) -> Any:
        """Parse JSON content"""
        try:
            # Try direct JSON parse
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON object/array from text
            # Look for JSON-like structures
            json_patterns = [
                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # JSON object
                r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # JSON array
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
            
            # If all parsing fails, try to fix common JSON issues
            fixed_content = DataParser._fix_json_format(content)
            try:
                return json.loads(fixed_content)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON: {content[:200]}")
                raise ValueError(f"Invalid JSON format: {content[:200]}")
    
    @staticmethod
    def _fix_json_format(content: str) -> str:
        """Try to fix common JSON format issues"""
        # Remove trailing commas
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        # Fix single quotes to double quotes
        content = re.sub(r"'([^']*)':", r'"\1":', content)
        content = re.sub(r":\s*'([^']*)'", r': "\1"', content)
        
        return content
    
    @staticmethod
    def _parse_for_excel(content: str) -> List[Dict[str, Any]]:
        """Parse content for Excel format (convert to list of dicts)"""
        # Try to parse as JSON first
        try:
            data = DataParser._parse_json(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
        except:
            pass
        
        # Try to parse as CSV
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return []
        
        # First line as headers
        headers = [h.strip() for h in lines[0].split(',')]
        result = []
        
        for line in lines[1:]:
            values = [v.strip() for v in line.split(',')]
            if len(values) == len(headers):
                result.append(dict(zip(headers, values)))
        
        return result
    
    @staticmethod
    def detect_format(content: str) -> str:
        """Auto-detect data format from content"""
        content_lower = content.lower().strip()
        
        # Check for JSON
        if content_lower.startswith('{') or content_lower.startswith('['):
            try:
                json.loads(content)
                return "json"
            except:
                pass
        
        # Check for markdown JSON code block
        if re.search(r'```(?:json)?\s*[\{\[]', content, re.IGNORECASE):
            return "json"
        
        # Check for CSV (has commas and newlines)
        lines = content.split('\n')
        if len(lines) > 1 and ',' in lines[0]:
            return "csv"
        
        # Default to text
        return "text"
