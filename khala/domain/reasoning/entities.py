"""Entities for Agentic Reasoning Modules (Module 13.1.2 - ARM)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

@dataclass
class ReasoningModule:
    """Represents a discovered reasoning module (code snippet)."""
    id: str
    module_code: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    discovery_iteration: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_module_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        module_code: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        discovery_iteration: int = 0,
        parent_module_id: Optional[str] = None,
        tags: List[str] = None
    ) -> 'ReasoningModule':
        return cls(
            id=str(uuid.uuid4()),
            module_code=module_code,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            discovery_iteration=discovery_iteration,
            parent_module_id=parent_module_id,
            tags=tags or []
        )

@dataclass
class ModuleEvaluation:
    """Evaluation of a reasoning module on a specific task."""
    id: str
    module_id: str
    task_description: str
    success: bool
    latency_ms: float
    tokens_used: int
    output_quality: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
