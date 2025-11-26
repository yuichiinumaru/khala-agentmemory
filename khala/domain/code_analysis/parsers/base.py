"""Base interface for code parsers."""

from abc import ABC, abstractmethod
from ..value_objects import ParsedCode

class CodeParser(ABC):
    """Abstract base class for code parsers."""
    
    @abstractmethod
    def parse(self, code: str) -> ParsedCode:
        """Parse the given code and return a ParsedCode object.
        
        Args:
            code: The source code string to parse.
            
        Returns:
            ParsedCode: The extracted structure and metadata.
        """
        pass
