"""Value objects for code analysis.

These structures hold the information extracted from source code.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class CodeElementType(Enum):
    FUNCTION = "function"
    CLASS = "class"
    IMPORT = "import"
    VARIABLE = "variable"

@dataclass
class CodeElement:
    """Base class for extracted code elements."""
    name: str
    line_number: int
    element_type: CodeElementType = field(init=False)

@dataclass
class ImportDefinition(CodeElement):
    """Represents an import statement."""
    module: str
    names: List[str]  # e.g., ["List", "Dict"] or ["*"]
    alias: Optional[str] = None
    
    def __post_init__(self):
        self.element_type = CodeElementType.IMPORT

@dataclass
class FunctionDefinition(CodeElement):
    """Represents a function or method definition."""
    args: List[str]
    return_type: str
    docstring: Optional[str]
    code: str
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    
    def __post_init__(self):
        self.element_type = CodeElementType.FUNCTION

@dataclass
class ClassDefinition(CodeElement):
    """Represents a class definition."""
    methods: List[FunctionDefinition]
    docstring: Optional[str]
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.element_type = CodeElementType.CLASS

@dataclass
class ParsedCode:
    """Container for all extracted elements from a code snippet."""
    imports: List[ImportDefinition] = field(default_factory=list)
    functions: List[FunctionDefinition] = field(default_factory=list)
    classes: List[ClassDefinition] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
