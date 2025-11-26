"""Service for code analysis."""

from typing import Dict, Type
from .value_objects import ParsedCode
from .parsers.base import CodeParser
from .parsers.python_parser import PythonCodeParser

class CodeAnalysisService:
    """Service for analyzing code structure."""
    
    def __init__(self):
        self._parsers: Dict[str, CodeParser] = {
            "python": PythonCodeParser(),
            "py": PythonCodeParser(),
        }
    
    def analyze_code(self, code: str, language: str = "python") -> ParsedCode:
        """Analyze the given code and return its structure.
        
        Args:
            code: The source code to analyze.
            language: The programming language of the code (default: "python").
            
        Returns:
            ParsedCode: The extracted structure.
            
        Raises:
            ValueError: If the language is not supported.
        """
        parser = self._parsers.get(language.lower())
        if not parser:
            raise ValueError(f"Unsupported language: {language}")
            
        return parser.parse(code)
