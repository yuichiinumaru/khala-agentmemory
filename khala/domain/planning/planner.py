"""Domain services for planning and decomposition."""

import logging
import json
import uuid
from dataclasses import dataclass, field, asdict
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
class VerificationResult:
    """Result of a plan verification."""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    score: float

@dataclass
class Plan:
    """A multi-step plan."""
    id: str
    goal: str
    steps: List[PlanStep]
    status: str = "created"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    verification_history: List[VerificationResult] = field(default_factory=list)

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
                model_id="gemini-2.5-flash", # Use smarter model for planning
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
            
    async def verify_plan(self, plan: Plan, context: str = "") -> VerificationResult:
        """Verify the validity and feasibility of a plan."""
        plan_dict = {
            "goal": plan.goal,
            "steps": [s.description for s in plan.steps]
        }

        prompt = f"""
        Review the following plan for errors, logical gaps, or safety issues.

        Plan:
        {json.dumps(plan_dict, indent=2)}

        Context:
        {context}

        Provide a verification result in JSON format:
        {{
            "is_valid": boolean,
            "issues": [list of strings],
            "suggestions": [list of strings],
            "score": float (0.0 to 1.0)
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash", # Use critic/verifier model role
                temperature=0.1
            )

            content = self._clean_json_response(response["content"])
            result_data = json.loads(content)

            result = VerificationResult(
                is_valid=result_data.get("is_valid", False),
                issues=result_data.get("issues", []),
                suggestions=result_data.get("suggestions", []),
                score=result_data.get("score", 0.0)
            )

            plan.verification_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Error verifying plan: {e}")
            # Return a fail-safe negative result
            return VerificationResult(False, [str(e)], [], 0.0)

    async def refine_plan(self, plan: Plan, verification_result: VerificationResult) -> Plan:
        """Refine a plan based on verification feedback."""
        prompt = f"""
        Original Goal: {plan.goal}

        Original Steps:
        {[s.description for s in plan.steps]}

        Issues Found:
        {verification_result.issues}

        Suggestions:
        {verification_result.suggestions}

        Please rewrite the plan to address these issues.
        Return a JSON list of strings (the new steps).
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.5-flash",
                temperature=0.2
            )

            content = self._clean_json_response(response["content"])
            step_descriptions = json.loads(content)

            new_steps = [
                PlanStep(id=str(uuid.uuid4()), description=desc)
                for desc in step_descriptions
            ]

            # Update the existing plan object
            plan.steps = new_steps
            return plan

        except Exception as e:
            logger.error(f"Error refining plan: {e}")
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
