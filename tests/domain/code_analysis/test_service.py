"""Tests for code analysis service."""

import pytest
from khala.domain.code_analysis.services import CodeAnalysisService
from khala.domain.code_analysis.value_objects import CodeElementType

def test_python_function_parsing():
    code = """
def my_function(a: int, b: str) -> bool:
    '''This is a docstring.'''
    return True
"""
    service = CodeAnalysisService()
    result = service.analyze_code(code, "python")
    
    assert len(result.functions) == 1
    func = result.functions[0]
    assert func.name == "my_function"
    assert func.args == ["a", "b"]
    assert func.return_type == "bool"
    assert func.docstring == "This is a docstring."
    assert func.element_type == CodeElementType.FUNCTION

def test_python_class_parsing():
    code = """
class MyClass(BaseClass):
    '''Class docstring.'''
    
    def method_one(self):
        pass
"""
    service = CodeAnalysisService()
    result = service.analyze_code(code, "python")
    
    assert len(result.classes) == 1
    cls = result.classes[0]
    assert cls.name == "MyClass"
    assert cls.bases == ["BaseClass"]
    assert cls.docstring == "Class docstring."
    assert len(cls.methods) == 1
    assert cls.methods[0].name == "method_one"

def test_python_imports():
    code = """
import os
from typing import List, Optional
import numpy as np
"""
    service = CodeAnalysisService()
    result = service.analyze_code(code, "python")
    
    assert len(result.imports) == 4
    # Check imports
    assert result.imports[0].name == "os"
    # typing imports are split
    assert result.imports[1].module == "typing"
    assert "List" in result.imports[1].names
    assert result.imports[2].module == "typing"
    assert "Optional" in result.imports[2].names
    assert result.imports[3].alias == "np"

def test_syntax_error():
    code = "def invalid_syntax("
    service = CodeAnalysisService()
    result = service.analyze_code(code, "python")
    
    assert len(result.errors) > 0
    assert "SyntaxError" in result.errors[0]
