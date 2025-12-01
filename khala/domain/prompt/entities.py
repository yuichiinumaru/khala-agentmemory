"""Entities for Prompt Optimization (Module 13)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid

@dataclass
class PromptCandidate:
    """Represents a generated prompt candidate in the genetic algorithm."""
    id: str
    task_id: str
    prompt_text: str
    instructions: str
    generation: int
    fitness_score: float = 0.0
    examples: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    mutations_applied: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        task_id: str,
        prompt_text: str,
        instructions: str,
        generation: int,
        parent_id: Optional[str] = None,
        examples: List[str] = None,
        mutations_applied: List[str] = None
    ) -> 'PromptCandidate':
        return cls(
            id=str(uuid.uuid4()),
            task_id=task_id,
            prompt_text=prompt_text,
            instructions=instructions,
            generation=generation,
            parent_id=parent_id,
            examples=examples or [],
            mutations_applied=mutations_applied or []
        )

@dataclass
class PromptEvaluation:
    """Evaluation metrics for a prompt candidate."""
    id: str
    prompt_id: str
    task_id: str
    accuracy: float
    efficiency: float
    human_preference: int = 0
    feedback_rules_triggered: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        prompt_id: str,
        task_id: str,
        accuracy: float,
        efficiency: float,
        human_preference: int = 0,
        feedback_rules_triggered: List[str] = None
    ) -> 'PromptEvaluation':
        return cls(
            id=str(uuid.uuid4()),
            prompt_id=prompt_id,
            task_id=task_id,
            accuracy=accuracy,
            efficiency=efficiency,
            human_preference=human_preference,
            feedback_rules_triggered=feedback_rules_triggered or []
        )
