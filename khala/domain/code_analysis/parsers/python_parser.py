"""Python implementation of CodeParser using the ast module."""

import ast
from typing import List, Optional, Any
from ..value_objects import (
    ParsedCode, 
    FunctionDefinition, 
    ClassDefinition, 
    ImportDefinition,
    CodeElementType
)
from .base import CodeParser

class PythonCodeParser(CodeParser):
    """Parses Python code using the ast module."""
    
    def parse(self, code: str) -> ParsedCode:
        """Parse Python code and extract structure."""
        parsed_code = ParsedCode()
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            parsed_code.errors.append(f"SyntaxError: {str(e)}")
            return parsed_code
            
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                parsed_code.imports.extend(self._extract_imports(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed_code.functions.append(self._extract_function(node, code))
            elif isinstance(node, ast.ClassDef):
                parsed_code.classes.append(self._extract_class(node, code))
                
        return parsed_code
    
    def _extract_imports(self, node: ast.AST) -> List[ImportDefinition]:
        imports = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportDefinition(
                    name=alias.name,
                    line_number=node.lineno,
                    module=alias.name,
                    names=[],
                    alias=alias.asname
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            for alias in node.names:
                imports.append(ImportDefinition(
                    name=f"{module}.{alias.name}",
                    line_number=node.lineno,
                    module=module,
                    names=[alias.name],
                    alias=alias.asname
                ))
        return imports

    def _extract_function(self, node: Any, source_code: str) -> FunctionDefinition:
        # Extract args
        args = [arg.arg for arg in node.args.args]
        
        # Extract return type
        return_type = "Any"
        if node.returns:
            return_type = self._get_annotation_str(node.returns)
            
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        # Extract decorators
        decorators = [self._get_decorator_str(d) for d in node.decorator_list]
        
        # Extract source segment (approximation)
        # In a real scenario, we might want exact slicing, but ast doesn't give end_lineno in older python versions reliably
        # For now, we'll store the name. Storing full code requires segment extraction logic.
        # We will store the full body as code for now if possible, or just the signature.
        # Let's try to extract the segment if end_lineno exists (Python 3.8+)
        func_code = ""
        if hasattr(node, 'end_lineno'):
            lines = source_code.splitlines()
            # lineno is 1-indexed
            func_lines = lines[node.lineno-1 : node.end_lineno]
            func_code = "\n".join(func_lines)
        
        return FunctionDefinition(
            name=node.name,
            line_number=node.lineno,
            args=args,
            return_type=return_type,
            docstring=docstring,
            code=func_code,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef)
        )

    def _extract_class(self, node: ast.ClassDef, source_code: str) -> ClassDefinition:
        docstring = ast.get_docstring(node)
        bases = [self._get_annotation_str(b) for b in node.bases]
        decorators = [self._get_decorator_str(d) for d in node.decorator_list]
        
        methods = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(child, source_code))
                
        return ClassDefinition(
            name=node.name,
            line_number=node.lineno,
            methods=methods,
            docstring=docstring,
            bases=bases,
            decorators=decorators
        )

    def _get_annotation_str(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation_str(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            value = self._get_annotation_str(node.value)
            slice_val = self._get_annotation_str(node.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        # Fallback for complex types
        return "ComplexType"

    def _get_decorator_str(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_annotation_str(node.func) # Simplified
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation_str(node.value)}.{node.attr}"
        return "decorator"
