"""
Format converter service for converting data between formats
"""
import json
import csv
import io
import logging
from typing import Any, List, Dict
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


class FormatConverter:
    """Converter for data formats"""
    
    @staticmethod
    def convert_to_json(data: Any) -> str:
        """
        Convert data to JSON string
        
        Args:
            data: Data to convert (dict, list, etc.)
        
        Returns:
            JSON string
        """
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def convert_to_csv(data: List[Dict[str, Any]]) -> str:
        """
        Convert data to CSV string
        
        Args:
            data: List of dictionaries
        
        Returns:
            CSV string
        """
        if not data:
            return ""
        
        # Use pandas for CSV conversion
        df = pd.DataFrame(data)
        
        # Convert to CSV string
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        csv_string = output.getvalue()
        output.close()
        
        return csv_string
    
    @staticmethod
    def convert_to_excel(data: List[Dict[str, Any]]) -> bytes:
        """
        Convert data to Excel bytes
        
        Args:
            data: List of dictionaries
        
        Returns:
            Excel file as bytes
        """
        if not data:
            # Return empty workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Data"
            output = io.BytesIO()
            wb.save(output)
            return output.getvalue()
        
        # Use pandas to create Excel
        df = pd.DataFrame(data)
        
        # Convert to Excel bytes
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        
        excel_bytes = output.getvalue()
        output.close()
        
        return excel_bytes
    
    @staticmethod
    def convert_format(
        data: Any,
        from_format: str,
        to_format: str
    ) -> Any:
        """
        Convert data from one format to another
        
        Args:
            data: Data to convert
            from_format: Source format (json, csv, excel, text)
            to_format: Target format (json, csv, excel, text)
        
        Returns:
            Converted data (string for json/csv/text, bytes for excel)
        """
        # Normalize data to list of dicts if needed
        normalized_data = FormatConverter._normalize_data(data, from_format)
        
        if to_format == "json":
            return FormatConverter.convert_to_json(normalized_data)
        elif to_format == "csv":
            return FormatConverter.convert_to_csv(normalized_data)
        elif to_format == "excel":
            return FormatConverter.convert_to_excel(normalized_data)
        else:  # text
            return str(normalized_data)
    
    @staticmethod
    def _normalize_data(data: Any, format: str) -> List[Dict[str, Any]]:
        """Normalize data to list of dictionaries"""
        if isinstance(data, list):
            # Check if list contains dicts
            if data and isinstance(data[0], dict):
                return data
            else:
                # Convert list of primitives to list of dicts
                return [{"value": item} for item in data]
        elif isinstance(data, dict):
            return [data]
        elif isinstance(data, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(data)
                return FormatConverter._normalize_data(parsed, "json")
            except:
                # Return as text
                return [{"text": data}]
        else:
            return [{"value": str(data)}]
