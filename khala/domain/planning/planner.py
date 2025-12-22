"""Domain services for planning and decomposition."""

import logging
import json
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

@dataclass
class PlanStep:
    """A single step in a plan."""
    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    sub_steps: List["PlanStep"] = field(default_factory=list)
    result: Optional[str] = None

@dataclass
class Plan:
    """A multi-step plan."""
    id: str
    goal: str
    steps: List[PlanStep]
    status: str = "created"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

class Planner:
    """Service for creating and decomposing plans."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        
    async def create_plan(self, goal: str, context: str = "") -> Plan:
        """Generate a high-level plan for a goal."""
        prompt = f"""
        Goal: {goal}
        
        Context:
        {context}
        
        Create a step-by-step plan to achieve this goal.
        Return a JSON list of strings, where each string is a step description.
        Example: ["Step 1 description", "Step 2 description"]
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-3-flash-preview", # Use smarter model for planning
                temperature=0.2
            )
            
            content = self._clean_json_response(response["content"])
            step_descriptions = json.loads(content)
            
            steps = [
                PlanStep(id=str(uuid.uuid4()), description=desc)
                for desc in step_descriptions
            ]
            
            return Plan(
                id=str(uuid.uuid4()),
                goal=goal,
                steps=steps
            )
            
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            raise
            
    async def decompose_step(self, step: PlanStep, context: str = "") -> None:
        """Decompose a complex step into sub-steps."""
        prompt = f"""
        Step to decompose: {step.description}
        
        Context:
        {context}
        
        Break this step down into 3-5 smaller, actionable sub-steps.
        Return a JSON list of strings.
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash",
                temperature=0.2
            )
            
            content = self._clean_json_response(response["content"])
            sub_step_descriptions = json.loads(content)
            
            step.sub_steps = [
                PlanStep(id=str(uuid.uuid4()), description=desc)
                for desc in sub_step_descriptions
            ]
            
        except Exception as e:
            logger.error(f"Error decomposing step: {e}")
            # Don't raise, just leave sub_steps empty
            
    def _clean_json_response(self, content: str) -> str:
        """Helper to extract JSON from LLM response."""
        if "```json" in content:
            return content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            return content.split("```")[1].split("```")[0].strip()
        return content.strip()
